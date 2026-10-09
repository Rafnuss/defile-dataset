"""Raw records -> the dataset: `surveys` and `observations`, with flagged corrections.

No row is ever removed. A correction either changes a value and keeps the original next to it
(`start_original`, `datetime_original`, ...), or only flags a row; every one adds a code to the
row's `flags` column (`;`-separated, see the FLAG_* constants). Users decide what to exclude:
the forecast drops flagged rows its model cannot use, a GBIF export may keep them.

Entry errors worth correcting at the source (in Trektellen) are also collected in `issues`, one
row per survey and issue, with the species and birds concerned.

See docs/dataset.md for the tables' columns and the rationale of each correction.
"""

from dataclasses import dataclass

import numpy as np
import pandas as pd

from defile_dataset.attributes import ATTRIBUTE_COLUMNS
from defile_dataset.read import EFFORT_SHEET, TREKTELLEN_FIRST_YEAR
from defile_dataset.site import NIGHT_SUN_ALTITUDE, TIMEZONE, civil_twilight
from defile_dataset.source_text import HISTORICAL_TEXT_COLUMNS, recover_historical_times
from defile_dataset.taxonomy import TAXON_COLUMNS, Taxonomy

# Audit threshold only: night periods remain unchanged and eligible for processing.
NIGHT_TOLERANCE = pd.Timedelta(minutes=45)

# Observation flags
FLAG_NO_TIME = "no_time"  # historical record without start/end: no survey
FLAG_NO_SURVEY = "no_survey"  # Trektellen entry whose count id is not in the header export
FLAG_DUPLICATE_SURVEY = "duplicate_survey"  # entry of a later overlapping survey
FLAG_TIME_ADJUSTED = "time_adjusted"  # legacy flag; no longer generated
FLAG_TIME_OUTSIDE_SURVEY = "time_outside_survey"  # timestamp further outside its survey
FLAG_UNTIMED_IN_TIMED_SURVEY = "untimed_in_timed_survey"
# Survey flags
FLAG_NO_ENTRIES = "no_entries"  # survey with no observation at all (see README)
FLAG_RECORDS_DELETED = "records_deleted"  # records deleted in the manual cleaning
FLAG_START_CLIPPED = "start_clipped_to_dawn"  # legacy; no longer generated
FLAG_END_CLIPPED = "end_clipped_to_dusk"  # legacy; no longer generated


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
HISTORICAL_SURVEY_COLUMNS = [
    "day_start",
    "day_end",
    "sheet",
    "observers",
    "weather",
    "remarks",
    "survey_complete",
    "weather_stop",
    "survey_comment",
]
# The effort sheet's decision columns (blank `survey_complete`: complete; blank `weather_stop`: no).
STATUS_COLUMNS = ["survey_complete", "weather_stop", "survey_comment"]
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
    *TAXON_COLUMNS,
    "count",
    "flags",
    "day_id",
    "time_resolution",
    "use_for_counts",
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
# Historical days whose records were all deleted in the manual cleaning of count_2021.xlsx
# (README -> Manual cleaning): surveyed, but not "nothing seen".
RECORDS_DELETED_DAYS = (pd.Timestamp("2021-10-29"),)

ISSUE_COLUMNS = [
    "date",
    "survey_id",
    "start",
    "end",
    "issue",
    "detail",
    "entries",
    "birds",
    "outside_minutes",
]


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
    return ts.tz_convert(TIMEZONE).strftime("%H:%M:%S")


def _time_range(t: pd.Series) -> str:
    a, b = _hm(t.min()), _hm(t.max())
    return a if a == b else f"{a}-{b}"


def _species_counts(g: pd.DataFrame, top: int = 4) -> str:
    """'Red Kite 85, Cormorant 74, ...' for a set of entries."""
    by = g.groupby("taxon_name_original")["count"].sum().sort_values(ascending=False)
    text = ", ".join(f"{k} {v:g}" for k, v in by.head(top).items())
    return text + (", ..." if len(by) > top else "")


# ---------------------------------------------------------------------------------------
# Historical data (count_2021.xlsx, 1966-2021)
# ---------------------------------------------------------------------------------------


def _survey_id(start: pd.Series, end: pd.Series) -> pd.Series:
    return (
        "H"
        + start.dt.tz_convert(TIMEZONE).dt.strftime("%Y%m%d-%H%M")
        + "-"
        + end.dt.tz_convert(TIMEZONE).dt.strftime("%H%M")
    )


def historical_tables(hist: pd.DataFrame, effort: pd.DataFrame, taxonomy: Taxonomy):
    """Returns (surveys, observations, issues). A survey is one (start, end) period.

    Days of the effort sheet without any record are surveys too, flagged `no_entries`.
    """
    h = hist.copy()
    for column in ATTRIBUTE_COLUMNS:
        if column not in h:
            h[column] = pd.NA
    surveyed = h["start"].notna() & h["end"].notna()
    h["survey_id"] = _survey_id(h["start"], h["end"]).where(surveyed)
    h["source"] = "historical"
    h["flags"] = ""

    surveys = h[surveyed].drop_duplicates("survey_id").copy()
    surveys["start_original"], surveys["end_original"] = surveys["start"], surveys["end"]
    surveys["duplicate_of"] = pd.NA

    # Before TREKTELLEN_FIRST_YEAR only: later days of the effort sheet are Trektellen counts.
    e = effort[
        ~effort["date"].isin(h["date"]) & (effort["date"].dt.year < TREKTELLEN_FIRST_YEAR)
    ].drop_duplicates(["date", "start", "end"])
    e = e.assign(
        survey_id=_survey_id(e["start"], e["end"]),
        source="historical",
        start_original=e["start"],
        end_original=e["end"],
        duplicate_of=pd.NA,
        flags=FLAG_NO_ENTRIES,
        day_start=e["start"],
        day_end=e["end"],
        sheet=EFFORT_SHEET,
    )
    # A day stopped by weather without recorded hours uses calendar bounds, never invented hours.
    date_only = e["start"].isna() & e["end"].isna()
    e.loc[date_only, "survey_id"] = (
        "H" + e.loc[date_only, "date"].dt.strftime("%Y%m%d") + "-weather-day"
    )
    e.loc[date_only, "start"] = (
        e.loc[date_only, "date"].dt.tz_localize(TIMEZONE).dt.tz_convert("UTC")
    )
    e.loc[date_only, "end"] = (
        (e.loc[date_only, "date"] + pd.Timedelta(days=1))
        .dt.tz_localize(TIMEZONE)
        .dt.tz_convert("UTC")
    )
    add_flag(e, date_only, "calendar_day_bounds")
    add_flag(e, e["date"].isin(RECORDS_DELETED_DAYS), FLAG_RECORDS_DELETED)
    # The reference's effort sheet holds daily narratives, not hourly headcounts/readings.
    metadata = effort.reindex(columns=["date", "observers", "weather", "remark"]).drop_duplicates(
        "date"
    )
    metadata = metadata.rename(columns={"remark": "remarks"})
    surveys = surveys.merge(metadata, on="date", how="left", validate="many_to_one")
    e = e.drop(columns=["observers", "weather", "remark"], errors="ignore").merge(
        metadata, on="date", how="left", validate="many_to_one"
    )
    surveys = pd.concat([surveys, e], ignore_index=True)
    # Coverage is interval-specific; daily observer notes must not spread exceptions.
    decisions = effort.reindex(columns=["date", "start", "end"] + STATUS_COLUMNS)
    decisions = decisions.loc[decisions[STATUS_COLUMNS].notna().any(axis=1)].drop_duplicates(
        ["date", "start", "end"], keep="last"
    )
    surveys = surveys.merge(
        decisions,
        on=["date", "start", "end"],
        how="left",
        suffixes=("", "_review"),
        validate="many_to_one",
    )
    for field in STATUS_COLUMNS:
        if field + "_review" in surveys:
            surveys[field] = surveys[field + "_review"].combine_first(surveys[field])
    surveys = surveys.reindex(columns=SURVEY_COLUMNS + HISTORICAL_SURVEY_COLUMNS)

    add_flag(h, ~surveyed, FLAG_NO_TIME)
    h["observation_id"] = "H-" + h["sheet"] + "-r" + h["row"].astype(str)
    h["trektellen_species_id"] = pd.NA
    h = h.rename(columns={"species": "taxon_name_original", **HISTORICAL_OBSERVATION_COLUMNS})
    h = recover_historical_times(h)
    h = taxonomy.add_to(h, "historical")
    h["day_id"] = "DEFILE-" + h["date"].dt.strftime("%Y%m%d")
    whole_day = (h["start"] == h["day_start"]) & (h["end"] == h["day_end"])
    h["time_resolution"] = np.where(surveyed & ~whole_day, "interval", "day")
    outside = h.datetime.notna() & surveyed & ((h.datetime < h.start) | (h.datetime > h.end))
    add_flag(h, outside, FLAG_TIME_OUTSIDE_SURVEY)
    h.loc[outside, "datetime"] = pd.NaT
    h.loc[outside, "time_resolution"] = "day"
    h.loc[outside, "time_text_status"] = "clock_outside_native_period"
    for field in ("comment", "remark"):
        h.loc[outside, field + "_residual"] = h.loc[outside, field]
    h.loc[h.datetime.notna(), "time_resolution"] = "point"
    h["use_for_counts"] = True
    obs = h[
        OBSERVATION_COLUMNS
        + list(HISTORICAL_OBSERVATION_COLUMNS.values())
        + ATTRIBUTE_COLUMNS
        + HISTORICAL_TEXT_COLUMNS
    ]
    issues = _issues_by_survey(
        h.loc[outside],
        surveys,
        "Timestamp outside period",
        lambda g, p: f"Historical clock {_time_range(g['datetime_original'])}, outside "
        f"{_hm(p['start'])}-{_hm(p['end'])}; retained at day level: {_species_counts(g)}.",
    )
    return surveys, obs, pd.DataFrame(issues, columns=ISSUE_COLUMNS)


# ---------------------------------------------------------------------------------------
# Trektellen (2022 on)
# ---------------------------------------------------------------------------------------


def _audit_daylight(s: pd.DataFrame, issues: list) -> None:
    """Audit unusual night periods without changing their times or processing flags."""
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
                f"{NIGHT_SUN_ALTITUDE:g}°); retained unchanged pending source review.",
                entries=0,
                birds=0,
            )
        )


def _mark_overlaps(s: pd.DataFrame) -> None:
    """Within each day, retain earliest start (native ID breaks ties); exclude later overlaps.

    Compare against retained periods only, so a chain does not exclude disjoint surveys.
    Night-spanning periods do not cause another day's count to be excluded.
    """
    for _, day in s.sort_values(["start", "id"]).groupby("date"):
        retained = []
        for i, row in day.iterrows():
            overlap = next(
                (
                    j
                    for j in retained
                    if row["start"] < s.at[j, "end"] and row["end"] > s.at[j, "start"]
                ),
                None,
            )
            if overlap is None:
                retained.append(i)
            else:
                s.at[i, "duplicate_of"] = s.at[overlap, "survey_id"]
                add_flag(s, s.index == i, FLAG_DUPLICATE_SURVEY)


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


def trektellen_tables(sightings: pd.DataFrame, counts: pd.DataFrame, taxonomy: Taxonomy):
    """Returns (surveys, observations, issues). A survey is one Trektellen count period."""
    issues = []

    s = counts.copy()
    s["survey_id"] = "T" + s["id"].astype(str)
    s["source"] = "trektellen"
    s["date"] = _local_date(s["start"])
    s["start_original"], s["end_original"] = s["start"], s["end"]
    s["duplicate_of"] = pd.NA
    s["flags"] = ""
    _audit_daylight(s, issues)
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
    for _, p in s[s["duplicate_of"].notna()].iterrows():
        sid = p["survey_id"]
        g = o[o["survey_id"] == sid]
        kept = s.loc[s["survey_id"] == p["duplicate_of"]].iloc[0]
        issues.append(
            dict(
                date=p["date"],
                survey_id=sid,
                start=p["start"],
                end=p["end"],
                issue="Overlapping periods",
                detail=f"Overlaps {kept['survey_id']} ({_hm(kept['start'])}-{_hm(kept['end'])}), "
                f"which starts first (native ID breaks ties) and is kept; later overlap excluded from processed totals: {_species_counts(g)}.",
                entries=len(g),
                birds=int(g["count"].sum()),
            )
        )

    # Audit original times even on excluded overlaps; then apply the processing policy.
    valid = ~no_survey
    start, end = period["start"].set_axis(o.index), period["end"].set_axis(o.index)
    outside = valid & ((o["datetime_original"] < start) | (o["datetime_original"] > end))
    add_flag(o, outside, FLAG_TIME_OUTSIDE_SURVEY)
    issues += _issues_by_survey(
        o[outside],
        s,
        "Timestamp outside period",
        lambda g, p: f"Timestamped {_time_range(g['datetime_original'])}, outside "
        f"{_hm(p['start'])}-{_hm(p['end'])}; retained at day level: {_species_counts(g)}.",
    )
    untimed = valid & o["datetime_original"].isna()
    add_flag(o, untimed, FLAG_UNTIMED_IN_TIMED_SURVEY)
    issues += _issues_by_survey(
        o[untimed],
        s,
        "Entry without time",
        lambda g, p: f"No hour; retained at day level: {_species_counts(g)}.",
    )
    o.loc[outside, "datetime"] = pd.NaT
    o["day_id"] = "DEFILE-" + o["date"].dt.strftime("%Y%m%d")
    o["time_resolution"] = np.where(o["datetime"].notna(), "point", "day")
    o["use_for_counts"] = ~duplicate

    for issue in issues:
        if issue["issue"] == "Period into the night":
            records = o[o["survey_id"] == issue["survey_id"]]
            issue["entries"] = len(records)
            issue["birds"] = int(records["count"].sum())
    o = taxonomy.add_to(o, "trektellen")
    add_flag(s, ~s["survey_id"].isin(o["survey_id"]), FLAG_NO_ENTRIES)
    surveys = s[SURVEY_COLUMNS + list(TREKTELLEN_SURVEY_COLUMNS.values())]
    obs = o[OBSERVATION_COLUMNS + list(TREKTELLEN_OBSERVATION_COLUMNS.values())]
    review = pd.DataFrame(issues, columns=ISSUE_COLUMNS)
    offsets = (
        pd.concat([start - o.datetime_original, o.datetime_original - end], axis=1)
        .max(axis=1)
        .dt.total_seconds()
        .div(60)
        .clip(lower=0)
    )
    review["outside_minutes"] = review.survey_id.map(offsets.groupby(o.survey_id).max()).where(
        review.issue.eq("Timestamp outside period")
    )
    return surveys, obs, review


def build(hist, effort, sightings, counts, taxonomy: Taxonomy) -> Dataset:
    hs, ho, hi = historical_tables(hist, effort, taxonomy)
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


def daily_counts(ds: Dataset) -> pd.DataFrame:
    """Daily reconciliation of retained source records, without filling missing hours."""
    o = ds.observations[ds.observations["use_for_counts"]].copy()
    for resolution in ("point", "interval", "day"):
        o[resolution + "_count"] = o["count"].where(o["time_resolution"] == resolution, 0)
    return (
        o.groupby(
            ["day_id", "date", "source", "taxon_name_original", "avibase_id", "taxon_kind"],
            dropna=False,
        )
        .agg(
            count=("count", "sum"),
            records=("observation_id", "size"),
            point_count=("point_count", "sum"),
            interval_count=("interval_count", "sum"),
            day_count=("day_count", "sum"),
            direction2=("direction2", "sum"),
            local=("local", "sum"),
        )
        .reset_index()
    )
