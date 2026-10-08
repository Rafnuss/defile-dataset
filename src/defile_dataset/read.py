"""Reading the raw files: parsing only.

Nothing is removed, merged or corrected here and every raw column is kept; times are converted
from local time (Europe/Paris) to UTC. Corrections live in `defile_dataset.build`, where each
one is flagged.
"""

import glob
import os
import re

import pandas as pd

from defile_dataset.site import TIMEZONE, TREKTELLEN_SITE_ID

HISTORICAL_FILE = os.path.join("historical", "count_2021.xlsx")
# Sheets of HISTORICAL_FILE holding records.
HISTORICAL_SHEETS = ("1966-2013", "2014-2016", "2017-2021")
# The day survey windows, 1966-2023, already merged into the startTimeDay/endTimeDay columns
# of the record sheets; read for the days it has and the record sheets do not.
EFFORT_SHEET = "Pression observation"

TREKTELLEN_DIR = "trektellen"
# count_2021.xlsx covers up to 2021, hand-cleaned and hour by hour, so Trektellen is read from
# 2022. The Trektellen 2021 export (`Trektellen_data_2422_2021.xlsx`, day totals only, no header
# export) is the same season -- 378,802 birds vs. 379,934 -- and is not a build input.
TREKTELLEN_FIRST_YEAR = 2022
TREKTELLEN_DATA_PATTERN = "Trektellen_data_{site}_{year}.xlsx"
TREKTELLEN_HEADER_PATTERN = "Trektellen_headerdata_{site}_{year}.xlsx"


def local_to_utc(local: pd.Series) -> pd.Series:
    """Naive local (Europe/Paris) datetimes -> UTC.

    The hour repeated when clocks go back (last Sunday of October, 02:00-03:00) is ambiguous
    and becomes NaT; it is at night, so in practice only mis-entered times hit it.
    """
    return local.dt.tz_localize(TIMEZONE, ambiguous="NaT").dt.tz_convert("UTC")


def _clock(times: pd.Series) -> pd.Series:
    """Excel time-of-day cells (time objects or 'HH:MM:SS' strings) -> Timedelta."""
    return pd.to_timedelta(pd.to_datetime(times, format="%H:%M:%S").dt.time.astype(str))


def read_historical(raw_dir: str) -> pd.DataFrame:
    """All records of `count_2021.xlsx` (1966-2021), one row per spreadsheet row.

    Adds `sheet`, `row` (the Excel row number, header = 1), `start`/`end` (the record's own
    period, UTC) and `day_start`/`day_end` (that day's whole survey window, UTC; the record's
    period where the sheet has none, i.e. 1966-2013). Every original column is kept.
    """
    path = os.path.join(raw_dir, HISTORICAL_FILE)
    sheets = []
    for s in HISTORICAL_SHEETS:
        df = pd.read_excel(path, sheet_name=s)
        sheets.append(df.assign(sheet=s, row=df.index + 2))
    df = pd.concat(sheets, ignore_index=True)
    start = df["date"] + _clock(df["startTime"])
    end = df["date"] + _clock(df["endTime"])
    df["start"] = local_to_utc(start)
    df["end"] = local_to_utc(end)
    df["day_start"] = local_to_utc((df["date"] + _clock(df["startTimeDay"])).fillna(start))
    df["day_end"] = local_to_utc((df["date"] + _clock(df["endTimeDay"])).fillna(end))
    return df


def read_effort(raw_dir: str) -> pd.DataFrame:
    """The EFFORT_SHEET of `count_2021.xlsx`: one row per survey day, `start`/`end` in UTC."""
    df = pd.read_excel(os.path.join(raw_dir, HISTORICAL_FILE), sheet_name=EFFORT_SHEET)
    df["start"] = local_to_utc(df["date"] + _clock(df["startTime"]))
    df["end"] = local_to_utc(df["date"] + _clock(df["endTime"]))
    return df


def trektellen_years(raw_dir: str) -> list[int]:
    """Years with both Trektellen exports present, from TREKTELLEN_FIRST_YEAR onward."""
    folder = os.path.join(raw_dir, TREKTELLEN_DIR)
    files = {
        kind: glob.glob(os.path.join(folder, pattern.format(site=TREKTELLEN_SITE_ID, year="*")))
        for kind, pattern in (
            ("data", TREKTELLEN_DATA_PATTERN),
            ("header", TREKTELLEN_HEADER_PATTERN),
        )
    }
    years = {
        kind: {int(re.search(r"_(\d{4})\.xlsx$", path).group(1)) for path in paths}
        for kind, paths in files.items()
    }
    years = {
        kind: {year for year in found if year >= TREKTELLEN_FIRST_YEAR}
        for kind, found in years.items()
    }
    missing_headers = sorted(years["data"] - years["header"])
    missing_data = sorted(years["header"] - years["data"])
    if missing_headers or missing_data:
        raise ValueError(
            "Trektellen exports must be paired by year; "
            f"missing headers for {missing_headers}, missing data for {missing_data}."
        )
    return sorted(years["data"])


def _timestamp_to_str(t):
    # `timestamp` mixes strings, time objects and NaN across yearly exports; converting to
    # one string column first would make pd.to_datetime infer a single format and silently
    # turn the rows that do not match it into NaT.
    if pd.isna(t) or t == "":
        return None
    if hasattr(t, "strftime"):
        return t.strftime("%H:%M:%S")
    return str(t)


def read_trektellen(raw_dir: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """All Trektellen exports for the site: `(sightings, counts)`.

    `sightings` is the data export, one row per entry, plus `export_row` (its position within
    its count in the export) and `datetime` (UTC; NaT when the entry has no timestamp).
    `counts` is the header export, one row per count period (any length: one hour, a whole
    day, ...), plus `start`/`end` in UTC (`start`/`stop` as exported are kept as
    `start_local`/`stop`). Every original column is kept.
    """
    folder = os.path.join(raw_dir, TREKTELLEN_DIR)
    sightings, counts = [], []
    for y in trektellen_years(raw_dir):
        for pattern, out in (
            (TREKTELLEN_DATA_PATTERN, sightings),
            (TREKTELLEN_HEADER_PATTERN, counts),
        ):
            path = os.path.join(folder, pattern.format(site=TREKTELLEN_SITE_ID, year=y))
            out.append(pd.read_excel(path))
    sightings = pd.concat(sightings, ignore_index=True)
    counts = pd.concat(counts, ignore_index=True)

    counts = counts.rename(columns={"start": "start_local"})
    counts["start"] = local_to_utc(pd.to_datetime(counts["start_local"]))
    counts["end"] = local_to_utc(pd.to_datetime(counts["stop"]))

    sightings["export_row"] = sightings.groupby("countid").cumcount() + 1
    sightings["date"] = pd.to_datetime(sightings["date"])
    clock = sightings["timestamp"].apply(_timestamp_to_str)
    has_time = clock.notna()
    local = (sightings["date"] + pd.to_timedelta(clock.where(has_time, "00:00:00"))).where(
        has_time, pd.NaT
    )
    sightings["datetime"] = local_to_utc(local)
    return sightings, counts
