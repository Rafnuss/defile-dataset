"""Tests for reading and correcting the raw records, on small synthetic inputs.

They don't read raw/: the real data is checked by `run_checks` on every build.
"""

import pandas as pd

from defile_dataset import build as B
from defile_dataset.checks import run_checks
from defile_dataset.read import local_to_utc
from defile_dataset.site import TIMEZONE, civil_twilight
from defile_dataset.taxonomy import AVILIST_VERSION, Taxonomy, resolve

RED_KITE = "avibase-451D6FC8"
TAXONOMY = Taxonomy(
    source_taxa=pd.DataFrame(
        {
            "source": ["historical", "historical", "trektellen", "trektellen"],
            "taxon_name_original": ["Milan royal", "Aucune espèce", "Red Kite", "Vulcain"],
            "trektellen_species_id": pd.array([None, None, 1, 983], dtype="Int64"),
            "avibase_id": [RED_KITE, None, RED_KITE, None],
            "kind": ["bird", "no_species", "bird", "non_bird"],
        }
    ),
    avilist=pd.DataFrame(
        {
            "scientific_name": ["Milvus milvus"],
            "english_name": ["Red Kite"],
            "taxon_rank": ["species"],
            "order": ["Accipitriformes"],
            "family": ["Accipitridae"],
        },
        index=pd.Index([RED_KITE]),
    ),
    ebird=pd.DataFrame(
        {
            "scientific_name": ["Milvus milvus"],
            "english_name": ["Red Kite (eBird)"],
            "taxon_rank": ["species"],
            "order": ["Accipitriformes"],
            "family": ["Accipitridae"],
            "ebird_code": ["redkit1"],
        },
        index=pd.Index([RED_KITE]),
    ),
)
DAY = "2023-08-01"
EMPTY_EFFORT = pd.DataFrame(
    {
        "date": pd.to_datetime([]),
        "start": pd.to_datetime([], utc=True),
        "end": pd.to_datetime([], utc=True),
    }
)


def utc(local: str) -> pd.Timestamp:
    return pd.Timestamp(local).tz_localize(TIMEZONE).tz_convert("UTC")


def test_local_to_utc_summer_time_and_ambiguous_hour():
    out = local_to_utc(pd.Series(pd.to_datetime(["2023-08-01 10:00", "2023-10-29 02:30"])))
    assert out[0] == pd.Timestamp("2023-08-01 08:00", tz="UTC")
    assert pd.isna(out[1])  # clocks go back at 03:00: 02:30 happens twice


def test_civil_twilight_is_plausible_in_summer():
    dawn, dusk = civil_twilight([pd.Timestamp(DAY)])
    assert "05:30" < dawn.iloc[0].tz_convert(TIMEZONE).strftime("%H:%M") < "06:15"
    assert "21:00" < dusk.iloc[0].tz_convert(TIMEZONE).strftime("%H:%M") < "21:45"


def _trektellen(entries: list[tuple], counts: list[tuple]):
    """entries: (dataid, countid, local time or None, speciesid, direction1);
    counts: (id, local start, local end, end day offset)."""
    s = pd.DataFrame(entries, columns=["dataid", "countid", "time", "speciesid", "direction1"])
    s["date"] = pd.Timestamp(DAY)
    s["speciesname"] = "Milan royal"
    for c in B.TREKTELLEN_OBSERVATION_COLUMNS:
        if c not in s:
            s[c] = None
    s["export_row"] = s.groupby("countid").cumcount() + 1
    local = pd.to_datetime(DAY + " " + s["time"].fillna("00:00")).where(s["time"].notna())
    s["datetime"] = local_to_utc(local)
    c = pd.DataFrame(counts, columns=["id", "start", "end", "days"])
    c["start"] = c["start"].map(lambda t: utc(f"{DAY} {t}"))
    c["end"] = [utc(f"{DAY} {t}") + pd.Timedelta(days=d) for t, d in zip(c["end"], c["days"])]
    for col in B.TREKTELLEN_SURVEY_COLUMNS:
        if col not in c:
            c[col] = None
    return s.drop(columns="time"), c.drop(columns="days")


def _flags(o, oid):
    return o.loc[o["observation_id"] == oid, "flags"].iloc[0]


def test_timestamps_are_adjusted_or_flagged_never_removed():
    s, c = _trektellen(
        [
            (1, 10, "06:30", 1, 5),
            (2, 10, "05:55", 1, 2),  # 5 min early: moved into the period
            (3, 10, "05:00", 1, 7),  # 1 h early: flagged
            (4, 10, None, 1, 9),  # untimed in a timed count: flagged
            (5, 99, "07:00", 1, 1),  # count missing from the header: flagged
        ],
        [(10, "06:00", "09:00", 0)],
    )
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    assert len(o) == len(s)
    assert _flags(o, "T1") == ""
    assert _flags(o, "T2") == B.FLAG_TIME_ADJUSTED
    adjusted = o[o["observation_id"] == "T2"].iloc[0]
    assert adjusted["datetime"] == utc(f"{DAY} 06:01")
    assert adjusted["datetime_original"] == utc(f"{DAY} 05:55")
    assert _flags(o, "T3") == B.FLAG_TIME_OUTSIDE_SURVEY
    assert _flags(o, "T4") == B.FLAG_UNTIMED_IN_TIMED_SURVEY
    assert _flags(o, "T5") == B.FLAG_NO_SURVEY
    assert set(issues["issue"]) == {"Timestamp outside period", "Entry without time"}
    # Names from AviList, eBird code and name kept alongside.
    assert o["english_name"].eq("Red Kite").all() and o["avibase_id"].eq(RED_KITE).all()
    assert o["ebird_english_name"].eq("Red Kite (eBird)").all()
    assert o["taxonomy_source"].eq(AVILIST_VERSION).all()


def test_overlapping_counts_keep_the_longest():
    s, c = _trektellen(
        [(1, 10, "08:40", 1, 5), (2, 11, "08:45", 1, 4)],
        [(10, "06:00", "12:00", 0), (11, "08:30", "09:30", 0)],
    )
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    assert surveys.set_index("survey_id")["duplicate_of"].to_dict()["T11"] == "T10"
    assert pd.isna(surveys.set_index("survey_id")["duplicate_of"]["T10"])
    assert _flags(o, "T2") == B.FLAG_DUPLICATE_SURVEY and _flags(o, "T1") == ""
    assert list(issues["issue"]) == ["Overlapping periods"]


def test_count_ending_the_next_morning_is_clipped_to_dusk():
    s, c = _trektellen([(1, 10, "12:00", 1, 3)], [(10, "07:00", "05:30", 1)])
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    _, dusk = civil_twilight([pd.Timestamp(DAY)])
    row = surveys.iloc[0]
    assert row["end"] == dusk.iloc[0]
    assert row["end_original"] == utc(f"{DAY} 05:30") + pd.Timedelta(days=1)
    assert row["flags"] == B.FLAG_END_CLIPPED
    assert list(issues["issue"]) == ["Period into the night"]


def test_observations_without_dataid_get_survey_based_ids():
    s, c = _trektellen(
        [(None, 10, "06:30", 1, 5), (None, 10, "07:30", 1, 1)], [(10, "06:00", "09:00", 0)]
    )
    _, o, _ = B.trektellen_tables(s, c, TAXONOMY)
    assert list(o["observation_id"]) == ["T10-e1", "T10-e2"]


def _historical(rows: list[tuple]):
    """rows: (French species, local start, local end, count), all on one day."""
    df = pd.DataFrame(rows, columns=["species", "start", "end", "count"])
    df["date"] = pd.Timestamp("2015-09-15")
    for c in ("start", "end"):
        df[c] = df[c].map(lambda t: utc(f"2015-09-15 {t}") if t else pd.NaT)
    df["day_start"], df["day_end"] = utc("2015-09-15 08:00"), utc("2015-09-15 12:00")
    df["sheet"], df["row"] = "2014-2016", df.index + 2
    for c in B.HISTORICAL_OBSERVATION_COLUMNS:
        if c not in df:
            df[c] = None
    return df


def test_historical_surveys_are_unique_periods():
    hist = _historical(
        [
            ("Milan royal", "08:00", "09:00", 3),
            ("Aucune espèce", "08:00", "09:00", 0),
            ("Milan royal", "10:00", "11:00", 1),
            ("Milan royal", None, None, 2),  # no time: flagged, no survey
        ]
    )
    surveys, o, _ = B.historical_tables(hist, EMPTY_EFFORT, TAXONOMY)
    assert list(surveys["survey_id"]) == ["H20150915-0800-0900", "H20150915-1000-1100"]
    assert o["observation_id"].tolist()[0] == "H-2014-2016-r2"
    assert o["flags"].tolist() == ["", "", "", B.FLAG_NO_TIME]
    assert o["taxon_kind"].tolist() == ["bird", "no_species", "bird", "bird"]
    assert pd.isna(o["avibase_id"].iloc[1])


def test_checks_pass_on_a_clean_build():
    s, c = _trektellen([(1, 10, "06:30", 1, 5)], [(10, "06:00", "09:00", 0)])
    hist = _historical([("Milan royal", "08:00", "09:00", 3)])
    ds = B.build(hist, EMPTY_EFFORT, s, c, TAXONOMY)
    status = {ch.name: ch.status for ch in run_checks(ds, TAXONOMY)}
    assert status["Unique ids"] == "pass"
    assert status["No overlapping surveys"] == "pass"
    assert status["Every observation has its survey"] == "pass"
    assert status["Taxa in source_taxa.csv"] == "pass"
    assert status["Avibase ids in the checklists"] == "pass"


def test_unknown_trektellen_id_is_reported():
    s, c = _trektellen([(1, 10, "06:30", 777, 5)], [(10, "06:00", "09:00", 0)])
    hist = _historical([("Milan royal", "08:00", "09:00", 3)])
    ds = B.build(hist, EMPTY_EFFORT, s, c, TAXONOMY)
    status = {ch.name: ch.status for ch in run_checks(ds, TAXONOMY)}
    assert status["Taxa in source_taxa.csv"] == "fail"


def test_resolve_falls_back_to_ebird_field_by_field():
    avilist = TAXONOMY.avilist.assign(english_name=[None])
    t = resolve(pd.Series([RED_KITE, "avibase-UNKNOWN"]), avilist, TAXONOMY.ebird)
    kite, unknown = t.iloc[0], t.iloc[1]
    assert (
        kite["scientific_name"] == "Milvus milvus" and kite["english_name"] == "Red Kite (eBird)"
    )
    assert kite["taxonomy_source"] == AVILIST_VERSION
    assert pd.isna(unknown["taxonomy_source"])


def test_effort_days_without_records_become_flagged_surveys():
    hist = _historical([("Milan royal", "08:00", "09:00", 3)])
    effort = pd.DataFrame({"date": pd.to_datetime(["2015-09-15", "2015-09-16"])})
    effort["start"] = [utc("2015-09-15 08:00"), utc("2015-09-16 08:00")]
    effort["end"] = [utc("2015-09-15 12:00"), utc("2015-09-16 12:00")]
    surveys, _, _ = B.historical_tables(hist, effort, TAXONOMY)
    empty = surveys[surveys["flags"] == B.FLAG_NO_ENTRIES]
    assert empty["survey_id"].tolist() == ["H20150916-0800-1200"]
    assert empty["sheet"].iloc[0] == "Pression observation"


def test_trektellen_count_without_entries_is_flagged():
    s, c = _trektellen(
        [(1, 10, "06:30", 1, 5)], [(10, "06:00", "09:00", 0), (11, "09:00", "10:00", 0)]
    )
    surveys, _, _ = B.trektellen_tables(s, c, TAXONOMY)
    assert surveys.set_index("survey_id")["flags"].to_dict() == {
        "T10": "",
        "T11": B.FLAG_NO_ENTRIES,
    }
