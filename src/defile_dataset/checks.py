"""Consistency checks of a built `Dataset`, run on every build and shown in the report."""

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from defile_dataset.build import (
    FLAG_DUPLICATE_SURVEY,
    FLAG_NO_SURVEY,
    FLAG_NO_TIME,
    FLAG_TIME_OUTSIDE_SURVEY,
    NIGHT_TOLERANCE,
    Dataset,
    has_flag,
)
from defile_dataset.site import NIGHT_SUN_ALTITUDE, civil_twilight

LONG_SURVEY_WARNING = pd.Timedelta(hours=16)  # a July dawn-to-dusk day is ~15 h 20


@dataclass
class Check:
    name: str
    status: str  # "pass" | "warn" | "fail"
    detail: str
    rows: pd.DataFrame = field(default_factory=pd.DataFrame)


def _check(name, bad: pd.DataFrame, detail: str, severity="fail") -> Check:
    return Check(name, "pass" if bad.empty else severity, detail, bad)


def run_checks(ds: Dataset) -> list[Check]:
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
    night = s[
        (s["start"] < s["date"].map(dawn) - NIGHT_TOLERANCE)
        | (s["end"] > s["date"].map(dusk) + NIGHT_TOLERANCE)
    ]
    checks.append(
        _check(
            "Surveys in daylight",
            night,
            f"{len(night)} survey(s) start or end more than "
            f"{NIGHT_TOLERANCE.total_seconds() / 60:.0f} min into the night (sun below "
            f"{NIGHT_SUN_ALTITUDE:g}°). By source: {night['source'].value_counts().to_dict()}.",
            "warn",
        )
    )

    bad = s[dur > LONG_SURVEY_WARNING]
    checks.append(
        _check(
            f"Surveys up to {LONG_SURVEY_WARNING.total_seconds() / 3600:.0f} h",
            bad,
            f"{len(bad)} survey(s) longer: likely a mis-entered start or end.",
            "warn",
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

    unm = o[o["english_name"].isna()]
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
            "Taxa in taxonomy.csv",
            by,
            f"{len(unm)} observation(s) of {len(by)} taxa are not in taxonomy/taxonomy.csv "
            "(no English or scientific name).",
            "warn",
        )
    )

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
