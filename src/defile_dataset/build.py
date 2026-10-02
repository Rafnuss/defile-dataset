"""Raw records -> the dataset: `surveys` and `observations`, with flagged corrections.

No row is ever removed. A correction either changes a value and keeps the original next to it
(`start_original`, `datetime_original`, ...), or only flags a row; every one adds a code to the
row's `flags` column (`;`-separated, see the FLAG_* constants). Users decide what to exclude:
the forecast drops flagged rows its model cannot use, a GBIF export may keep them.

Entry errors worth correcting at the source (in Trektellen) are also collected in `issues`, one
row per survey and issue, with the species and birds concerned.

See README.md for the tables' columns and the rationale of each correction.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from defile_dataset.site import NIGHT_SUN_ALTITUDE, TIMEZONE, civil_twilight

# Trektellen: an entry timestamped up to this long outside its count period is moved just
# inside it (`time_adjusted`); further out, it is flagged `time_outside_survey`.
TIMESTAMP_TOLERANCE = pd.Timedelta(minutes=10)
TIMESTAMP_NUDGE = pd.Timedelta(minutes=1)
# Trektellen: a count period reaching further than this into the night (sun below
# NIGHT_SUN_ALTITUDE) is clipped to dawn/dusk. Counts entered the same evening end at most
# ~30 min after dusk; every period beyond 45 min was entered days to months later.
NIGHT_TOLERANCE = pd.Timedelta(minutes=45)
# Trektellen: a survey counts as timed when fewer than this share of its entries lack a time;
# its untimed entries are then flagged `untimed_in_timed_survey`.
UNTIMED_SHARE_TIMED_SURVEY = 0.5

# Observation flags
FLAG_NO_TIME = "no_time"  # historical record without start/end: no survey
FLAG_NO_SURVEY = "no_survey"  # Trektellen entry whose count id is not in the header export
FLAG_DUPLICATE_SURVEY = "duplicate_survey"  # entry of a survey overlapping a longer one
FLAG_TIME_ADJUSTED = "time_adjusted"  # timestamp moved into its survey (TIMESTAMP_TOLERANCE)
FLAG_TIME_OUTSIDE_SURVEY = "time_outside_survey"  # timestamp further outside its survey
FLAG_UNTIMED_IN_TIMED_SURVEY = "untimed_in_timed_survey"
# Survey flags
FLAG_START_CLIPPED = "start_clipped_to_dawn"
FLAG_END_CLIPPED = "end_clipped_to_dusk"

TAXON_COLUMNS = {
    "English name": "english_name",
    "scientific name": "scientific_name",
    "species_code": "ebird_code",
    "taxon_concept_id": "avibase_id",
    "category": "taxon_category",
    "order": "order",
    "family": "family",
}

SURVEY_COLUMNS = [
    "survey_id",
    "source",
    "date",
    "start",
    "end",
    "start_original",
    "end_original",
    "duplicate_of",
    "flags",
]
HISTORICAL_SURVEY_COLUMNS = ["day_start", "day_end", "sheet"]
# Header-export fields kept as exported (renamed only where the name would be ambiguous).
TREKTELLEN_SURVEY_COLUMNS = {
    "id": "trektellen_count_id",
    "observers": "observers",
    "observersactive": "observers_active",
    "observerspresent": "observers_present",
    "weather": "weather",
    "windspeed_bfr": "wind_speed_bft",
    "wind_ms": "wind_speed_ms",
    "winddirection": "wind_direction",
    "cloudcover": "cloud_cover",
    "cloudheight": "cloud_height",
    "precipitation": "precipitation",
    "visibility": "visibility",
    "temperature": "temperature",
    "hpa": "pressure_hpa",
    "counttype": "count_type",
    "remarks": "remarks",
    "created": "created",
    "createdby": "created_by",
    "changed": "changed",
    "changedby": "changed_by",
}

OBSERVATION_COLUMNS = [
    "observation_id",
    "survey_id",
    "source",
    "date",
    "datetime",
    "datetime_original",
    "taxon_name_original",
    "trektellen_species_id",
    *TAXON_COLUMNS.values(),
    "count",
    "flags",
]
HISTORICAL_OBSERVATION_COLUMNS = {
    "sheet": "sheet",
    "row": "row",
    "time": "time_local",
    "ID liste": "in_list",
    "estimation": "estimation",
    "detail": "detail",
    "details": "details",
    "comment": "comment",
    "comment_list": "list_comment",
    "remark": "remark",
}
TREKTELLEN_OBSERVATION_COLUMNS = {
    "dataid": "trektellen_data_id",
    "countid": "trektellen_count_id",
    "export_row": "export_row",
    "timestamp": "timestamp_local",
    "direction2": "direction2",
    "local": "local",
    "remarkable": "remarkable",
    "remarkablelocal": "remarkable_local",
    "age": "age",
    "sex": "sex",
    "plumage": "plumage",
    "remark": "remark",
    "height": "height",
    "location": "location",
    "migtype": "migration_type",
    "counttype": "count_type",
    "exactdirection1": "exact_direction1",
    "exactdirection2": "exact_direction2",
    "sightingdirection": "sighting_direction",
    "groupid": "group_id",
}
# Integer columns empty for one of the sources, kept integer (not float) in the CSV.
INTEGER_OBSERVATION_COLUMNS = [
    "row",
    "trektellen_species_id",
    "trektellen_data_id",
    "trektellen_count_id",
    "export_row",
    "group_id",
]
ISSUE_COLUMNS = ["date", "survey_id", "start", "end", "issue", "detail", "entries", "birds"]


@dataclass
class Dataset:
    surveys: pd.DataFrame
    observations: pd.DataFrame
    issues: pd.DataFrame


def add_flag(df: pd.DataFrame, mask, flag: str) -> None:
    mask = np.asarray(mask, dtype=bool)
    df.loc[mask, "flags"] = (df.loc[mask, "flags"] + ";" + flag).str.strip(";")


def has_flag(flags: pd.Series, flag: str) -> pd.Series:
    return flags.fillna("").str.split(";").apply(lambda f: flag in f)


def _local_date(ts: pd.Series) -> pd.Series:
    return ts.dt.tz_convert(TIMEZONE).dt.tz_localize(None).dt.normalize()


def _hm(ts) -> str:
    return ts.tz_convert(TIMEZONE).strftime("%H:%M")


def _time_range(t: pd.Series) -> str:
    a, b = _hm(t.min()), _hm(t.max())
    return a if a == b else f"{a}-{b}"


def _species_counts(g: pd.DataFrame, top: int = 4) -> str:
    """'Red Kite 85, Cormorant 74, ...' for a set of entries."""
    by = g.groupby("taxon_name_original")["count"].sum().sort_values(ascending=False)
    text = ", ".join(f"{k} {v:g}" for k, v in by.head(top).items())
    return text + (", ..." if len(by) > top else "")


def with_taxonomy(df: pd.DataFrame, taxonomy: pd.DataFrame, left_on: str, right_on: str):
    """Add the TAXON_COLUMNS of taxonomy.csv (NaN when unmatched)."""
    tax = taxonomy[[right_on, *TAXON_COLUMNS]].dropna(subset=[right_on])
    if right_on == "trektellen_species_id":
        tax = tax.astype({right_on: int})
    tax = tax.rename(columns={right_on: "_key", **TAXON_COLUMNS})
    out = df.merge(tax, how="left", left_on=left_on, right_on="_key").drop(columns="_key")
    assert len(out) == len(df), f"taxonomy.csv has duplicate {right_on}"
    return out


# ---------------------------------------------------------------------------------------
# Historical data (count_2021.xlsx, 1966-2021)
# ---------------------------------------------------------------------------------------


def historical_tables(hist: pd.DataFrame, taxonomy: pd.DataFrame):
    """Returns (surveys, observations, issues). A survey is one (start, end) period."""
    h = hist.copy()
    surveyed = h["start"].notna() & h["end"].notna()
    h["survey_id"] = (
        "H"
        + h["start"].dt.tz_convert(TIMEZONE).dt.strftime("%Y%m%d-%H%M")
        + "-"
        + h["end"].dt.tz_convert(TIMEZONE).dt.strftime("%H%M")
    ).where(surveyed)
    h["source"] = "historical"
    h["flags"] = ""

    surveys = h[surveyed].drop_duplicates("survey_id").copy()
    surveys["start_original"], surveys["end_original"] = surveys["start"], surveys["end"]
    surveys["duplicate_of"] = pd.NA
    surveys = surveys[SURVEY_COLUMNS + HISTORICAL_SURVEY_COLUMNS]

    add_flag(h, ~surveyed, FLAG_NO_TIME)
    h["observation_id"] = "H-" + h["sheet"] + "-r" + h["row"].astype(str)
    h["datetime"] = h["datetime_original"] = pd.NaT
    h["trektellen_species_id"] = pd.NA
    h = h.rename(columns={"species": "taxon_name_original", **HISTORICAL_OBSERVATION_COLUMNS})
    h = with_taxonomy(h, taxonomy, left_on="taxon_name_original", right_on="species")
    obs = h[OBSERVATION_COLUMNS + list(HISTORICAL_OBSERVATION_COLUMNS.values())]
    return surveys, obs, pd.DataFrame(columns=ISSUE_COLUMNS)


# ---------------------------------------------------------------------------------------
# Trektellen (2022 on)
# ---------------------------------------------------------------------------------------


def _clip_to_daylight(s: pd.DataFrame, issues: list) -> None:
    """Count periods reaching into the night: clipped to civil dawn/dusk, flagged."""
    dawn, dusk = civil_twilight(s["date"])
    dawn, dusk = s["date"].map(dawn), s["date"].map(dusk)
    early = s["start"] < dawn - NIGHT_TOLERANCE
    late = s["end"] > dusk + NIGHT_TOLERANCE
    for i in s.index[early | late]:
        lt = bool(late[i])
        when, limit = (s.at[i, "end"], dusk[i]) if lt else (s.at[i, "start"], dawn[i])
        issues.append(
            dict(
                date=s.at[i, "date"],
                survey_id=s.at[i, "survey_id"],
                start=s.at[i, "start"],
                end=s.at[i, "end"],
                issue="Period into the night",
                detail=f"{'Ends' if lt else 'Starts'} "
                f"{when.tz_convert(TIMEZONE):%Y-%m-%d %H:%M}, "
                f"{abs(when - limit).total_seconds() / 3600:.1f} h "
                f"{'after dusk' if lt else 'before dawn'} ({_hm(limit)}, sun at "
                f"{NIGHT_SUN_ALTITUDE:g}°); clipped to {'dusk' if lt else 'dawn'}.",
                entries=0,
                birds=0,
            )
        )
    s.loc[early, "start"] = dawn[early]
    s.loc[late, "end"] = dusk[late]
    add_flag(s, early, FLAG_START_CLIPPED)
    add_flag(s, late, FLAG_END_CLIPPED)


def _mark_overlaps(s: pd.DataFrame) -> None:
    """Overlapping count periods count the same birds twice: all but the longest of each
    overlapping group get `duplicate_of` = the kept survey."""
    p = s.sort_values("start")
    group = (p["start"] >= p["end"].cummax().shift().fillna(p["start"].iloc[0])).cumsum()
    keep = (p["end"] - p["start"]).groupby(group).idxmax()
    kept_id = group.map(s.loc[keep.values, "survey_id"].set_axis(keep.index))
    dup = p["survey_id"] != kept_id
    s.loc[dup[dup].index, "duplicate_of"] = kept_id[dup]


def _issues_by_survey(rows: pd.DataFrame, surveys: pd.DataFrame, issue: str, detail) -> list:
    out = []
    for sid, g in rows.groupby("survey_id"):
        p = surveys.loc[surveys["survey_id"] == sid].iloc[0]
        out.append(
            dict(
                date=p["date"],
                survey_id=sid,
                start=p["start"],
                end=p["end"],
                issue=issue,
                detail=detail(g, p),
                entries=len(g),
                birds=int(g["count"].sum()),
            )
        )
    return out


def trektellen_tables(sightings: pd.DataFrame, counts: pd.DataFrame, taxonomy: pd.DataFrame):
    """Returns (surveys, observations, issues). A survey is one Trektellen count period."""
    issues = []

    s = counts.copy()
    s["survey_id"] = "T" + s["id"].astype(str)
    s["source"] = "trektellen"
    s["date"] = _local_date(s["start"])
    s["start_original"], s["end_original"] = s["start"], s["end"]
    s["duplicate_of"] = pd.NA
    s["flags"] = ""
    _clip_to_daylight(s, issues)
    _mark_overlaps(s)
    s = s.rename(columns=TREKTELLEN_SURVEY_COLUMNS)

    o = sightings.copy()
    o["source"] = "trektellen"
    o["flags"] = ""
    o["survey_id"] = "T" + o["countid"].astype(str)
    # 2022-2023 exports have no dataid: those ids are only stable within this export.
    o["observation_id"] = np.where(
        o["dataid"].notna(),
        "T" + o["dataid"].astype("Int64").astype(str),
        o["survey_id"] + "-e" + o["export_row"].astype(str),
    )
    o = o.rename(
        columns={
            "speciesid": "trektellen_species_id",
            "speciesname": "taxon_name_original",
            "direction1": "count",
            **TREKTELLEN_OBSERVATION_COLUMNS,
        }
    )
    o["datetime_original"] = o["datetime"]

    period = o[["survey_id"]].merge(
        s[["survey_id", "start", "end", "duplicate_of"]],
        on="survey_id",
        how="left",
        indicator=True,
    )
    no_survey = (period["_merge"] != "both").values
    duplicate = period["duplicate_of"].notna().values
    add_flag(o, no_survey, FLAG_NO_SURVEY)
    add_flag(o, duplicate, FLAG_DUPLICATE_SURVEY)
    for sid, g in o[duplicate].groupby("survey_id"):
        p = s.loc[s["survey_id"] == sid].iloc[0]
        kept = s.loc[s["survey_id"] == p["duplicate_of"]].iloc[0]
        issues.append(
            dict(
                date=p["date"],
                survey_id=sid,
                start=p["start"],
                end=p["end"],
                issue="Overlapping periods",
                detail=f"Overlaps {kept['survey_id']} ({_hm(kept['start'])}-{_hm(kept['end'])}), "
                f"which is longer and kept; this one is flagged duplicate: {_species_counts(g)}.",
                entries=len(g),
                birds=int(g["count"].sum()),
            )
        )

    valid = ~no_survey & ~duplicate
    start, end = period["start"].set_axis(o.index), period["end"].set_axis(o.index)
    t = o["datetime"]
    early = valid & (t < start) & ((start - t) < TIMESTAMP_TOLERANCE)
    o.loc[early, "datetime"] = start[early] + TIMESTAMP_NUDGE
    late = valid & (o["datetime"] >= end) & ((o["datetime"] - end) < TIMESTAMP_TOLERANCE)
    o.loc[late, "datetime"] = end[late] - TIMESTAMP_NUDGE
    add_flag(o, early | late, FLAG_TIME_ADJUSTED)

    outside = valid & ((o["datetime"] < start) | (o["datetime"] > end))
    add_flag(o, outside, FLAG_TIME_OUTSIDE_SURVEY)
    issues += _issues_by_survey(
        o[outside],
        s,
        "Timestamp outside period",
        lambda g, p: f"Timestamped {_time_range(g['datetime'])}, more than "
        f"{TIMESTAMP_TOLERANCE.total_seconds() / 60:.0f} min outside the period "
        f"{_hm(p['start'])}-{_hm(p['end'])}: {_species_counts(g)}.",
    )

    inside = valid & ~outside
    untimed_share = o["datetime"].isna()[inside].groupby(o["survey_id"][inside]).mean()
    timed_survey = o["survey_id"].map(untimed_share < UNTIMED_SHARE_TIMED_SURVEY).eq(True)
    untimed = inside & timed_survey & o["datetime"].isna()
    add_flag(o, untimed, FLAG_UNTIMED_IN_TIMED_SURVEY)
    # Untimed entries of local birds only (no migrating bird) are routine, not an error.
    issues += _issues_by_survey(
        o[untimed & (o["count"] > 0)],
        s,
        "Entry without time",
        lambda g, p: "No time, in a count otherwise timed, so it cannot be placed in the "
        f"day: {_species_counts(g)}.",
    )

    o = with_taxonomy(
        o, taxonomy, left_on="trektellen_species_id", right_on="trektellen_species_id"
    )
    surveys = s[SURVEY_COLUMNS + list(TREKTELLEN_SURVEY_COLUMNS.values())]
    obs = o[OBSERVATION_COLUMNS + list(TREKTELLEN_OBSERVATION_COLUMNS.values())]
    return surveys, obs, pd.DataFrame(issues, columns=ISSUE_COLUMNS)


def build(hist, sightings, counts, taxonomy) -> Dataset:
    hs, ho, hi = historical_tables(hist, taxonomy)
    ts, to, ti = trektellen_tables(sightings, counts, taxonomy)
    surveys = (
        pd.concat([hs, ts], ignore_index=True)
        .sort_values(["start", "survey_id"], kind="stable")
        .reset_index(drop=True)
    )
    observations = pd.concat([ho, to], ignore_index=True)
    observations = observations.astype({c: "Int64" for c in INTEGER_OBSERVATION_COLUMNS})
    surveys = surveys.astype({"trektellen_count_id": "Int64"})
    order = observations["survey_id"].map(dict(zip(surveys["survey_id"], surveys.index)))
    observations = (
        observations.assign(_order=order)
        .sort_values(["date", "_order", "datetime"], kind="stable", na_position="last")
        .drop(columns="_order")
        .reset_index(drop=True)
    )
    found = [i for i in (hi, ti) if len(i)]
    issues = pd.concat(found, ignore_index=True) if found else ti
    issues = issues.sort_values(["date", "survey_id"])
    return Dataset(surveys, observations, issues.reset_index(drop=True))
