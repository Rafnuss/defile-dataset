"""Tests for reading and correcting the raw records, on small synthetic inputs.

They don't read raw/: the real data is checked by `run_checks` on every build.
"""

import pandas as pd
import pytest

from defile_dataset import build as B
from defile_dataset.checks import run_checks
from defile_dataset.read import local_to_utc, trektellen_years
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


def test_trektellen_years_requires_paired_exports(tmp_path):
    folder = tmp_path / "trektellen"
    folder.mkdir()
    (folder / "Trektellen_data_2422_2021.xlsx").touch()  # legacy export is not read
    (folder / "Trektellen_data_2422_2025.xlsx").touch()
    with pytest.raises(ValueError, match=r"missing headers for \[2025\]"):
        trektellen_years(tmp_path)
    (folder / "Trektellen_headerdata_2422_2025.xlsx").touch()
    assert trektellen_years(tmp_path) == [2025]
    (folder / "Trektellen_data_2422_2026.xlsx").touch()
    with pytest.raises(ValueError, match=r"missing headers for \[2026\]"):
        trektellen_years(tmp_path)


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


def test_outside_period_offsets_measure_early_and_late_entries():
    s, c = _trektellen([(1, 10, '05:55', 1, 2), (2, 11, '09:05', 1, 3), (3, 12, '09:06', 1, 4)],
                       [(10, '06:00', '09:00', 0), (11, '06:00', '09:00', 0), (12, '06:00', '09:00', 0)])
    _, _, issues = B.trektellen_tables(s, c, TAXONOMY)
    assert issues.loc[issues.issue.eq('Timestamp outside period'), 'outside_minutes'].tolist() == [5, 5, 6]


def test_outside_timestamps_become_daily_without_losing_source_times():
    s, c = _trektellen(
        [
            (1, 10, "06:30", 1, 5),
            (2, 10, "05:55", 1, 2),  # 5 min early: daily fallback, original retained
            (3, 10, "05:00", 1, 7),  # 1 h early: flagged
            (4, 10, None, 1, 9),  # untimed in a timed count: flagged
            (5, 99, "07:00", 1, 1),  # count missing from the header: flagged
        ],
        [(10, "06:00", "09:00", 0)],
    )
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    assert issues.loc[issues.issue.eq('Timestamp outside period'), 'outside_minutes'].tolist() == [60]
    assert len(o) == len(s)
    assert _flags(o, "T1") == ""
    assert _flags(o, "T2") == B.FLAG_TIME_OUTSIDE_SURVEY
    adjusted = o[o["observation_id"] == "T2"].iloc[0]
    assert pd.isna(adjusted["datetime"])
    assert adjusted["datetime_original"] == utc(f"{DAY} 05:55")
    assert _flags(o, "T3") == B.FLAG_TIME_OUTSIDE_SURVEY
    assert o["use_for_counts"].all()
    assert o.loc[o["observation_id"].isin(["T2", "T3", "T4"]), "time_resolution"].eq("day").all()
    assert o["count"].sum() == 24
    assert _flags(o, "T4") == B.FLAG_UNTIMED_IN_TIMED_SURVEY
    assert _flags(o, "T5") == B.FLAG_NO_SURVEY
    assert set(issues["issue"]) == {"Timestamp outside period", "Entry without time"}
    # Names from AviList, with the eBird code alongside.
    assert o["english_name"].eq("Red Kite").all() and o["avibase_id"].eq(RED_KITE).all()
    assert o["ebird_code"].eq("redkit1").all()
    assert o["taxonomy_source"].eq(AVILIST_VERSION).all()


def test_overlapping_counts_keep_first_even_when_later_is_longer():
    s, c = _trektellen(
        [(1, 10, "08:40", 1, 5), (2, 11, "08:45", 1, 4)],
        [(10, "06:00", "09:00", 0), (11, "08:30", "12:00", 0)],
    )
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    assert surveys.set_index("survey_id")["duplicate_of"].to_dict()["T11"] == "T10"
    assert pd.isna(surveys.set_index("survey_id")["duplicate_of"]["T10"])
    assert _flags(o, "T2") == B.FLAG_DUPLICATE_SURVEY and _flags(o, "T1") == ""
    assert list(issues["issue"]) == ["Overlapping periods"]
    assert o.loc[o["use_for_counts"], "count"].sum() == 5
    assert o.loc[~o["use_for_counts"], "count"].sum() == 4


def test_night_period_is_audited_but_kept_unchanged_without_processing_flag():
    s, c = _trektellen([(1, 10, "12:00", 1, 3)], [(10, "07:00", "05:30", 1)])
    surveys, o, issues = B.trektellen_tables(s, c, TAXONOMY)
    _, dusk = civil_twilight([pd.Timestamp(DAY)])
    row = surveys.iloc[0]
    assert row["end"] == row["end_original"]
    assert row["end_original"] == utc(f"{DAY} 05:30") + pd.Timedelta(days=1)
    assert row["flags"] == ""
    assert o["use_for_counts"].all()
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


def test_daily_metadata_does_not_create_effort_or_duplicate_counts():
    hist = _historical([("Milan royal", "08:00", "09:00", 3), ("Milan royal", "10:00", "11:00", 1)])
    effort = pd.DataFrame({
        "date": [pd.Timestamp("2015-09-15")],
        "start": pd.to_datetime([None], utc=True), "end": pd.to_datetime([None], utc=True),
        "observers": ["A (08–09); B (10–11)"],
        "weather": ["Couvert le matin, éclaircies ensuite"], "remark": ["Visiteurs : 2"],
    })
    surveys, counts, _ = B.historical_tables(hist, effort, TAXONOMY)
    assert len(surveys) == 2 and len(counts) == 2 and counts["count"].sum() == 4
    assert surveys["observers"].tolist() == [effort.observers.iloc[0]] * 2
    assert surveys["weather"].tolist() == [effort.weather.iloc[0]] * 2
    assert surveys["remarks"].tolist() == ["Visiteurs : 2"] * 2
    assert counts["list_comment"].isna().all()
    assert "observers_active" not in surveys  # no inferred quantitative effort


def test_reviewed_coverage_applies_to_its_interval_only():
    hist = _historical([("Milan royal", "08:00", "09:00", 3), ("Milan royal", "10:00", "11:00", 1)])
    effort = hist[["date", "start", "end"]].copy()
    effort["survey_coverage"] = ["complete", "partial"]
    effort["survey_coverage_comment"] = ["Counted throughout", "Interrupted"]
    surveys, counts, _ = B.historical_tables(hist, effort, TAXONOMY)
    assert len(surveys) == 2 and counts["count"].sum() == 4
    assert surveys["survey_coverage"].tolist() == ["complete", "partial"]
    assert surveys["survey_coverage_comment"].tolist() == ["Counted throughout", "Interrupted"]


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


def test_daily_fallback_conserves_counts_and_directions():
    s, c = _trektellen(
        [(1, 10, "09:30", 1, 12), (2, 10, "10:30", 1, 8),
         (3, 10, None, 1, 5), (4, 10, "08:59", 1, 3)],
        [(10, "09:00", "11:00", 0)],
    )
    s["direction2"], s["local"] = [0, 0, 2, 0], [0, 0, 0, 1]
    surveys, observations, issues = B.trektellen_tables(s, c, TAXONOMY)
    daily = B.daily_counts(B.Dataset(surveys, observations, issues)).iloc[0]
    assert daily["count"] == 28
    assert daily["point_count"] == 20 and daily["day_count"] == 8
    assert daily["direction2"] == 2 and daily["local"] == 1
    assert observations["datetime_original"].notna().sum() == 3
    assert observations["datetime"].notna().sum() == 2


def test_overlap_chain_keeps_disjoint_first_and_third_periods():
    s, c = _trektellen(
        [(1, 10, "08:30", 1, 1), (2, 11, "09:30", 1, 2), (3, 12, "10:30", 1, 3)],
        [(10, "08:00", "09:00", 0), (11, "08:30", "10:30", 0),
         (12, "10:00", "11:00", 0)],
    )
    _, observations, _ = B.trektellen_tables(s, c, TAXONOMY)
    assert observations.loc[observations["use_for_counts"], "observation_id"].tolist() == ["T1", "T3"]


def test_report_links_filters_and_escaped_source_text():
    from defile_dataset.report import render

    s, c = _trektellen([(1, 10, None, 1, 5)], [(10, "06:00", "09:00", 0)])
    s["speciesname"] = '<script>alert("source")</script>'
    surveys, observations, issues = B.trektellen_tables(s, c, TAXONOMY)
    from defile_dataset.checks import Check
    document = render([Check('Entry without time', 'warn', 'Inspect source period', issues,
                             key='untimed', columns=('date','survey_id','detail'))], {})
    assert '<h3><span class="en">Entry without time' in document
    assert 'Inspect source period' in document
    assert 'href="https://www.trektellen.org/count/edit/10"' in document
    assert 'href="https://www.trektellen.org/count/view/2422/20230801"' in document
    assert 'finding-search' in document
    assert 'All 25951 entries' not in document
    assert '<script>alert("source")</script>' not in document
    assert '&lt;script&gt;' in document


def test_consolidated_tables_preserve_precision_keys_and_direction_counts():
    import json
    from defile_dataset.consolidate import consolidate, daily_from_tables, validate_tables
    from defile_dataset.package import descriptor

    hist = _historical([("Milan royal", "08:00", "09:00", 3), ("Aucune espèce", "08:00", "09:00", 0)])
    hist["detail"] = ["3x adultes", None]
    sightings, headers = _trektellen(
        [(1, 10, "08:30", 1, 12), (2, 10, None, 1, 5),
         (3, 10, "07:59", 1, 7), (4, 11, "09:30", 1, 282)],
        [(10, "08:00", "10:00", 0), (11, "09:00", "11:00", 0)],
    )
    sightings["direction2"], sightings["local"] = [2, 1, 0, 9], [0, 0, 4, 8]
    sightings["remark"] = "bird&#039;s note"
    ds = B.build(hist, EMPTY_EFFORT, sightings, headers, TAXONOMY)
    count, survey, taxa = consolidate(ds, TAXONOMY)
    assert all(c.status == 'pass' for c in validate_tables(count, survey, taxa, ds))
    assert "T11" not in survey.survey_id.tolist() and "T4" not in count.count_id.tolist()
    indexed = count.set_index("count_id")
    assert indexed.loc["T1", "datetime"] == "2023-08-01T06:30:00Z"
    assert indexed.loc["T1", "survey_id"] == "T10"
    assert indexed.loc[["T2", "T3"], "datetime"].tolist() == ["2023-08-01"] * 2
    assert indexed.loc[["T2", "T3"], "survey_id"].isna().all()
    assert pd.isna(indexed.loc["H-2014-2016-r2", "datetime"])
    assert pd.isna(indexed.loc["H-2014-2016-r2", "count_local"])
    assert indexed.loc["H-2014-2016-r2", "remark"] == "detail: 3x adultes"
    assert indexed.loc["T1", "remark"] == "remark: bird's note"
    assert "H-2014-2016-r3" not in count.count_id.tolist()
    assert "kind" not in taxa.columns
    assert survey.remark.fillna("").str.contains("no species").any()
    assert taxa.trektellen_species_id.tolist() == ["1"]
    assert json.loads(taxa.iloc[0].source_taxa)[0]["taxon_name_original"] == "Milan royal"
    day = daily_from_tables(count, survey).query("date == '2023-08-01'").iloc[0]
    assert day["count"] == 24 and day.count_reverse == 3 and day.count_local == 4
    for resource in descriptor()["resources"]:
        if resource["name"] not in ("count", "survey", "taxonomy"):
            continue
        table = {"count": count, "survey": survey, "taxonomy": taxa}[resource["name"]]
        assert [field["name"] for field in resource["schema"]["fields"]] == table.columns.tolist()


def test_presence_only_is_not_a_numerical_count():
    from defile_dataset.consolidate import consolidate, daily_from_tables, validate_tables

    hist = _historical([("Milan royal", "08:00", "09:00", 0)])
    hist["estimation"] = "x"
    sightings, headers = _trektellen([(1, 10, "08:30", 1, 1)], [(10, "08:00", "09:00", 0)])
    ds = B.build(hist, EMPTY_EFFORT, sightings, headers, TAXONOMY)
    count, survey, taxa = consolidate(ds, TAXONOMY)
    assert all(c.status == 'pass' for c in validate_tables(count, survey, taxa, ds))
    presence = count.loc[count.count_estimation.eq("x")].iloc[0]
    assert pd.isna(presence["count"])
    day = daily_from_tables(count, survey).query("date == '2015-09-15'").iloc[0]
    assert pd.isna(day["count"]) and pd.isna(day.count_reverse)


def test_bird_selection_preserves_empty_surveys_and_unidentified_birds():
    from defile_dataset.consolidate import consolidate, validate_tables

    taxonomy = Taxonomy(
        pd.concat([TAXONOMY.source_taxa, pd.DataFrame([{
            'source': 'trektellen', 'taxon_name_original': 'Species unidentified',
            'trektellen_species_id': 480, 'avibase_id': 'avibase-AF0D818A', 'kind': 'bird',
        }])], ignore_index=True),
        TAXONOMY.avilist,
        pd.concat([TAXONOMY.ebird, pd.DataFrame([{
            'scientific_name': 'Aves sp.', 'english_name': 'bird sp.', 'taxon_rank': 'spuh',
            'order': None, 'family': None, 'ebird_code': 'bird1',
        }], index=['avibase-AF0D818A'])]),
    )
    hist = _historical([('Aucune espèce', '08:00', '09:00', 0)])
    sightings, headers = _trektellen(
        [(1, 10, '08:30', 983, 8), (2, 11, '10:30', 480, 3)],
        [(10, '08:00', '09:00', 0), (11, '10:00', '11:00', 0)],
    )
    ds = B.build(hist, EMPTY_EFFORT, sightings, headers, taxonomy)
    count, survey, taxa = consolidate(ds, taxonomy)
    assert all(c.status == 'pass' for c in validate_tables(count, survey, taxa, ds))
    assert count.count_id.tolist() == ['T2']
    assert count.taxon_id.tolist() == ['avibase-AF0D818A']
    assert count['count'].tolist() == [3]
    assert len(survey) == 3 and 'T10' in survey.survey_id.tolist()
    assert survey.remark.fillna('').str.contains('no species').sum() == 1
    assert len(ds.observations) == 3  # full source ledger is untouched


def test_date_only_non_survey_uses_calendar_bounds_without_recorded_effort():
    hist = _historical([("Milan royal", "08:00", "09:00", 3)])
    effort = pd.DataFrame({
        "date": pd.to_datetime(["2015-10-25"]),
        "start": pd.to_datetime([None], utc=True), "end": pd.to_datetime([None], utc=True),
        "survey_coverage": ["none"], "survey_coverage_comment": ["Evidence status: inferred."],
    })
    surveys, counts, _ = B.historical_tables(hist, effort, TAXONOMY)
    day = surveys.set_index("survey_id").loc["H20151025-not-surveyed"]
    assert day.end - day.start == pd.Timedelta(hours=25)  # Local DST transition day.
    assert pd.isna(day.start_original) and pd.isna(day.end_original)
    assert pd.isna(day.day_start) and pd.isna(day.day_end)
    assert "calendar_day_bounds" in day['flags']
    assert "inferred" in day.survey_coverage_comment
    assert counts['count'].sum() == 3


def test_daylight_audit_measures_a_period_wholly_before_dawn():
    sightings, headers = _trektellen([(1, 10, '00:30', 1, 5)], [(10, '00:00', '01:00', 0)])
    surveys, observations, issues = B.trektellen_tables(sightings, headers, TAXONOMY)
    daylight = next(c for c in run_checks(B.Dataset(surveys, observations, issues), TAXONOMY) if c.name == 'Surveys into the night')
    row = daylight.rows.iloc[0]
    assert row.civil_dawn < row.sunrise < row.sunset < row.civil_dusk
    assert row.night_minutes == 60 and row.minutes_before_sunrise == 60 and row.minutes_after_sunset == 0


def test_split_historical_rows_keep_totals_dates_and_auditable_ids():
    from defile_dataset.attributes import historical_attributes, quantity_components
    from defile_dataset.consolidate import consolidate, validate_tables
    hist = _historical([('Milan royal', '08:00', '09:00', 5)])
    hist['details'] = '1x mâle adulte / 2x femelle adulte'
    hist['detail'] = hist.details
    crosswalk = pd.read_csv('config/attributes/historical_attributes.csv', dtype=str)
    values, audit = historical_attributes(hist, crosswalk)
    ds = B.build(hist.join(values), EMPTY_EFFORT, *_trektellen([(1, 10, '10:30', 1, 7)], [(10, '10:00', '11:00', 0)]), TAXONOMY)
    parts = quantity_components(audit)
    count, survey, taxa = consolidate(ds, TAXONOMY, parts)
    assert count.loc[count.count_id.str.startswith('H'), 'count'].tolist() == [1, 2, 2]
    assert all(c.status == 'pass' for c in validate_tables(count, survey, taxa, ds, parts))
    changed = count.copy()
    changed.loc[0, 'count'] += 1
    assert next(c for c in validate_tables(changed, survey, taxa, ds, parts) if c.name == 'count values preserved').status == 'fail'
    changed = count.copy()
    changed.loc[0, 'count_id'] += '-extra'
    assert validate_tables(changed, survey, taxa, ds, parts)[0].status == 'fail'


def test_source_conservation_returns_auditable_failure_rows():
    from defile_dataset.consolidate import consolidate, validate_tables
    hist = _historical([('Milan royal', '08:00', '09:00', 3)])
    sightings, headers = _trektellen([(1, 10, '08:30', 1, 5)], [(10, '08:00', '09:00', 0)])
    ds = B.build(hist, EMPTY_EFFORT, sightings, headers, TAXONOMY)
    count, survey, taxa = consolidate(ds, TAXONOMY)
    count.loc[0, 'count'] = 4
    result = validate_tables(count, survey, taxa, ds)
    failed = next(c for c in result if c.name == 'count values preserved')
    assert failed.status == 'fail'
    assert failed.rows[['released_value', 'source_value']].iloc[0].tolist() == [4, 3]
    missing = validate_tables(count.iloc[:0].reset_index(drop=True), survey, taxa, ds)
    assert next(c for c in missing if c.name == 'Eligible source rows retained once').status == 'fail'


def test_night_audit_keeps_short_overlap_and_long_audit_keeps_below_warning():
    from defile_dataset.site import civil_twilight
    sightings, headers = _trektellen([(1, 10, '08:30', 1, 5)], [(10, '08:00', '09:00', 0)])
    surveys, observations, issues = B.trektellen_tables(sightings, headers, TAXONOMY)
    dawn, _ = civil_twilight(surveys.date)
    surveys.loc[0, 'start'] = dawn.iloc[0]-pd.Timedelta(minutes=5)
    surveys.loc[0, 'end'] = dawn.iloc[0]+pd.Timedelta(minutes=10)
    checks = run_checks(B.Dataset(surveys, observations, issues), TAXONOMY)
    night = next(c for c in checks if c.name == 'Surveys into the night')
    assert night.rows.night_minutes.tolist() == [5]
    surveys.loc[0, 'end'] = surveys.loc[0, 'start']+pd.Timedelta(hours=14)
    long = next(c for c in run_checks(B.Dataset(surveys, observations, issues), TAXONOMY) if c.name == 'Long surveys')
    assert long.rows.duration_hours.tolist() == [14]
    assert long.status == 'pass'
