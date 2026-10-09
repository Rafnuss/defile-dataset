"""Readable naming preserves source lineage, quantities and survey associations."""
import pandas as pd

from defile_dataset.identities import readable_ids


def records():
    survey = pd.DataFrame(
        [
            dict(
                survey_id="T10",
                datetime="2026-09-13T22:30:00Z/2026-09-14T01:00:00Z",
                recording_era="trektellen",
                remark_processing=None,
            ),
            dict(
                survey_id="H19660911-weather-day",
                datetime="1966-09-10T23:00:00Z/1966-09-11T23:00:00Z",
                recording_era="notebook",
                remark_processing="Calendar-day bounds",
            ),
        ]
    )
    source = pd.DataFrame(
        [
            dict(
                observation_id="T20",
                survey_id="T10",
                date=pd.Timestamp("2026-09-14"),
                datetime=pd.Timestamp("2026-09-13T22:45:00Z"),
                sheet=None,
                time_local=None,
                time_resolution="timestamp",
                ebird_code="euhbuz1",
                taxon_name_original="Bondrée apivore",
            ),
            dict(
                observation_id="T21",
                survey_id="T10",
                date=pd.Timestamp("2026-09-14"),
                datetime=pd.Timestamp("2026-09-13T22:45:00Z"),
                sheet=None,
                time_local=None,
                time_resolution="timestamp",
                ebird_code="euhbuz1",
                taxon_name_original="Bondrée apivore",
            ),
            dict(
                observation_id="H-r2",
                survey_id=None,
                date=pd.Timestamp("2019-09-14"),
                datetime=pd.NaT,
                sheet="2017-2021",
                time_local=None,
                time_resolution="day",
                ebird_code=None,
                taxon_name_original="Rapace indéterminé",
            ),
        ]
    )
    count = pd.DataFrame(
        [
            dict(count_id="T20-normal", source_count_id="T20", survey_id="T10", count=3),
            dict(count_id="T20-reverse", source_count_id="T20", survey_id="T10", count=1),
            dict(count_id="T21-normal", source_count_id="T21", survey_id="T10", count=2),
            dict(count_id="H-r2-part1-normal", source_count_id="H-r2", survey_id=None, count=4),
        ]
    )
    interruptions = pd.DataFrame(
        [dict(native_survey_id="T10", time_precision="clock", interruption_id="I1")]
    )
    return count, survey, source, interruptions


def test_readable_ids_keep_local_dates_collisions_categories_and_provenance():
    count, survey, source, interruptions = records()
    result, events, gaps = readable_ids(count, survey, source, interruptions)
    assert events.survey_id.tolist() == ["T-20260914-0030", "B-19660911"]
    assert result.count_id.tolist() == [
        "T-20260914-0045-euhbuz1-normal",
        "T-20260914-0045-euhbuz1-reverse",
        "T-20260914-0045-euhbuz1-02-normal",
        "N-20190914-rapace-indetermine-part1-normal",
    ]
    pd.testing.assert_frame_equal(
        result.drop(columns=["count_id", "survey_id"]),
        count.drop(columns=["count_id", "survey_id"]),
    )
    assert events.source_survey_id.tolist() == survey.survey_id.tolist()
    assert result.survey_id.iloc[0] == gaps.native_survey_id.iloc[0] == events.survey_id.iloc[0]
    assert pd.isna(result.survey_id.iloc[-1])
    shuffled, _, _ = readable_ids(
        count.iloc[::-1], survey.iloc[::-1], source.iloc[::-1], interruptions
    )
    pd.testing.assert_series_equal(result.count_id, shuffled.count_id.sort_index())


def test_corrected_record_changes_readable_id_without_changing_source_id():
    count, survey, source, interruptions = records()
    original, _, _ = readable_ids(count, survey, source, interruptions)
    source.loc[0, "ebird_code"] = "osprey"
    updated, _, _ = readable_ids(count, survey, source, interruptions)
    assert updated.count_id.iloc[0] != original.count_id.iloc[0]
    assert updated.source_count_id.tolist() == original.source_count_id.tolist()


def test_timed_flock_id_uses_its_released_clock_and_keeps_source_lineage():
    count, survey, source, interruptions = records()
    count.loc[0, "count_id"] = "T20-time1-normal"
    count.loc[0, "datetime"] = "2026-09-13T23:15:00Z"
    result, _, _ = readable_ids(count, survey, source, interruptions)
    assert result.count_id.iloc[0] == "T-20260914-0115-euhbuz1-time1-normal"
    assert result.source_count_id.iloc[0] == "T20"


def test_reviewed_taxonomy_id_uses_target_code_and_retains_source_identity():
    count, survey, source, interruptions = records()
    source["avibase_id"] = ["old", "old", "unidentified"]
    count["taxon_id"] = ["new", "old", "old", "unidentified"]
    count.loc[0, "count_id"] = "T20-tax1-normal"
    taxa = pd.DataFrame(
        dict(taxon_id=["new", "old", "unidentified"], ebird_code=["turdus1", "euhbuz1", "bird1"])
    )
    result, _, _ = readable_ids(count, survey, source, interruptions, taxa)
    assert result.count_id.iloc[0] == "T-20260914-0045-turdus1-tax1-normal"
    assert result.source_count_id.tolist() == count.source_count_id.tolist()


def test_recorded_historical_clock_interval_start_and_curated_day():
    count, survey, source, interruptions = records()
    source.loc[0, ["sheet", "datetime", "time_local"]] = ["2017-2021", pd.NaT, "09:15:00"]
    source.loc[1, ["sheet", "datetime", "time_resolution"]] = ["2014-2016", pd.NaT, "interval"]
    survey.loc[0, ["survey_id", "recording_era"]] = ["I1-weather", "curated"]
    survey.loc[0, "datetime"] = "2026-09-13T22:00:00Z/2026-09-14T22:00:00Z"
    interruptions.loc[0, "time_precision"] = "day"
    result, events, _ = readable_ids(count, survey, source, interruptions)
    assert result.count_id.iloc[0] == "N-20260914-0915-euhbuz1-normal"
    assert events.survey_id.iloc[0] == "C-20260914"
    # A recorded historical subdaily interval contributes its own start.
    survey.loc[0, ["survey_id", "recording_era"]] = ["T10", "spreadsheet"]
    survey.loc[0, "datetime"] = "2026-09-14T06:00:00Z/2026-09-14T07:00:00Z"
    result, _, _ = readable_ids(count, survey, source, interruptions)
    assert result.count_id.iloc[2] == "S-20260914-0800-euhbuz1-normal"
