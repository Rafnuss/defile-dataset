"""Consistency checks of a built `Dataset`, run on every build and shown in the report."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from defile_dataset.build import (
    FLAG_DUPLICATE_SURVEY,
    FLAG_NO_SURVEY,
    FLAG_NO_TIME,
    FLAG_TIME_OUTSIDE_SURVEY,
    Dataset,
    has_flag,
)
from defile_dataset.site import civil_twilight
from defile_dataset.taxonomy import (
    AVILIST_VERSION,
    EBIRD_VERSION,
    KIND_BIRD,
    SOURCE_TAXA_FILE,
    Taxonomy,
)

LONG_SURVEY_WARNING = pd.Timedelta(hours=16)
LONG_SURVEY_MINIMUM = pd.Timedelta(hours=12)


@dataclass
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail" | "info"
    detail: str
    rows: pd.DataFrame = field(default_factory=pd.DataFrame)
    action: str = ""
    file: str = ""
    columns: tuple = ()
    key: str = ""
    group: str = "Counts and data integrity"
    filter_column: str = ""
    filter_threshold: float = 0


def _check(name, bad: pd.DataFrame, detail: str, severity="fail") -> Check:
    return Check(name, "pass" if bad.empty else severity, detail, bad)


def run_checks(ds: Dataset, taxonomy: Taxonomy) -> list[Check]:
    s, o = ds.surveys, ds.observations
    checks = []

    dup = pd.concat(
        [
            s[s["survey_id"].duplicated(keep=False)][["survey_id"]],
            o[o["observation_id"].duplicated(keep=False)][["observation_id"]],
        ]
    )
    checks.append(_check("Unique ids", dup, f"{len(dup)} duplicated survey/observation id(s)."))

    orphan_ok = has_flag(o["flags"], FLAG_NO_TIME) | has_flag(o["flags"], FLAG_NO_SURVEY)
    orphan = o[~o["survey_id"].isin(s["survey_id"]) & ~orphan_ok]
    checks.append(
        _check(
            "Every observation has its survey",
            orphan,
            f"{len(orphan)} observation(s) refer to a survey that does not exist (besides those "
            f"flagged {FLAG_NO_TIME}/{FLAG_NO_SURVEY}).",
        )
    )

    dur = s["end"] - s["start"]
    bad = s[dur <= pd.Timedelta(0)]
    checks.append(_check("Positive durations", bad, f"{len(bad)} survey(s) with end <= start."))

    p = s[s["duplicate_of"].isna()].sort_values("start").reset_index(drop=True)
    idx = np.flatnonzero(p["start"].values[1:] < p["end"].cummax().values[:-1])
    bad = p.loc[np.unique(np.r_[idx, idx + 1])]
    checks.append(
        _check(
            "No overlapping surveys",
            bad,
            f"{len(idx)} survey(s) overlap an earlier one (surveys marked duplicate_of excluded): "
            "the same birds would be counted twice.",
        )
    )

    dawn, dusk = civil_twilight(s["date"])
    # Weather stops with calendar-day bounds are not timed surveys.
    calendar = (
        s.get("weather_stop", pd.Series(False, index=s.index)).fillna(False).astype(bool)
        & s["start_original"].isna()
    )
    night = s.loc[~calendar].copy()
    if not night.empty:
        sunrise, sunset = civil_twilight(night["date"], threshold_deg=-0.833)
        night["sunrise"] = night.date.map(sunrise)
        night["sunset"] = night.date.map(sunset)
        night["civil_dawn"] = night.date.map(dawn)
        night["civil_dusk"] = night.date.map(dusk)
        night["duration_hours"] = (night.end - night.start).dt.total_seconds() / 3600
        night["minutes_before_sunrise"] = (
            ((night[["end", "sunrise"]].min(axis=1) - night.start).dt.total_seconds() / 60)
            .clip(lower=0)
            .round(1)
        )
        night["minutes_after_sunset"] = (
            ((night.end - night[["start", "sunset"]].max(axis=1)).dt.total_seconds() / 60)
            .clip(lower=0)
            .round(1)
        )
        night["night_minutes"] = (
            (
                (night[["end", "civil_dawn"]].min(axis=1) - night.start).dt.total_seconds() / 60
            ).clip(lower=0)
            + (
                (night.end - night[["start", "civil_dusk"]].max(axis=1)).dt.total_seconds() / 60
            ).clip(lower=0)
        ).round(1)
    checks.append(
        _check(
            "Surveys into the night",
            night.loc[night.night_minutes.gt(0)],
            "Minutes before civil dawn or after civil dusk (sun below −6°). Sunrise and sunset are shown for context.",
            "warn",
        )
    )
    long = night.loc[dur.loc[night.index] > LONG_SURVEY_MINIMUM].copy()
    checks.append(
        Check(
            "Long surveys",
            "warn"
            if long.duration_hours.gt(LONG_SURVEY_WARNING.total_seconds() / 3600).any()
            else "pass",
            "End minus start. All periods over 12 hours are retained; the initial review threshold is 16 hours.",
            long,
        )
    )

    t = o.merge(s[["survey_id", "start", "end"]], on="survey_id", how="inner")
    out = t[
        t["datetime"].notna()
        & ~has_flag(t["flags"], FLAG_TIME_OUTSIDE_SURVEY)
        & ~has_flag(t["flags"], FLAG_DUPLICATE_SURVEY)  # not time-checked: dropped anyway
        & ((t["datetime"] < t["start"]) | (t["datetime"] > t["end"]))
    ]
    checks.append(
        _check(
            "Timestamps inside their survey",
            out,
            f"{len(out)} timed observation(s) outside their survey and not flagged "
            f"{FLAG_TIME_OUTSIDE_SURVEY} (or {FLAG_DUPLICATE_SURVEY}).",
        )
    )

    unm = o[o["taxon_kind"].isna()]
    by = (
        unm.groupby(["source", "taxon_name_original", "trektellen_species_id"], dropna=False)[
            "count"
        ]
        .agg(observations="size", birds="sum")
        .reset_index()
        .sort_values("observations", ascending=False)
    )
    checks.append(
        _check(
            "Taxa in source_taxa.csv",
            by,
            f"{len(unm)} observation(s) of {len(by)} source taxa (historical name or Trektellen "
            f"id) are missing from {SOURCE_TAXA_FILE}: add a row for each, with its avibase_id.",
        )
    )

    st = taxonomy.source_taxa
    bad = st[(st["kind"] == KIND_BIRD) & st["avibase_id"].isna()]
    checks.append(
        _check(
            "Every bird taxon has an avibase_id",
            bad,
            f"{len(bad)} bird row(s) of {SOURCE_TAXA_FILE} without avibase_id.",
        )
    )

    t = taxonomy.taxa
    bad = st.merge(t[t["taxonomy_source"].isna()][["avibase_id"]], on="avibase_id")
    checks.append(
        _check(
            "Avibase ids in the checklists",
            bad,
            f"{len(bad)} row(s) of {SOURCE_TAXA_FILE} have an avibase_id found in neither "
            f"{AVILIST_VERSION} nor {EBIRD_VERSION} (after an upgrade: usually a split). Re-map "
            "them.",
        )
    )
    by = t.groupby("taxonomy_source").size().to_dict()
    checks.append(Check("Taxonomy source", "pass", f"Taxa named from each checklist: {by}."))

    synth = o[(o["source"] == "trektellen") & o["trektellen_data_id"].isna()]
    by = synth.groupby(synth["date"].dt.year).size().rename("observations").reset_index()
    checks.append(
        _check(
            "Stable observation ids",
            by,
            f"{len(synth)} Trektellen observation(s) have no Trektellen data id in the export, by "
            f"year {dict(zip(by['date'], by['observations']))}: their ids (survey + export row) "
            "change if the export changes. Re-export those years from Trektellen.",
            "warn",
        )
    )
    return checks
