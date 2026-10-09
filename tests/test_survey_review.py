"""Weather stops are complete with no bird; absences leave no survey; counts never move off their day."""
import pandas as pd

from defile_dataset.survey_review import (
    EMPTY_HOUR_NOTE,
    empty_survey_review,
    integrate_historical_gaps,
    integrate_interruptions,
    interruption_review,
    validate_historical_gaps,
)


def test_weather_stops_cut_headers_and_fill_the_time_between_surveys(tmp_path):
    events = pd.DataFrame(
        [
            dict(
                interruption_id="I1",
                scope="day",
                datetime="2024-09-26T00:00:00+02:00/2024-09-27T00:00:00+02:00",
                time_precision="day",
                effect="weather",
                note="Rain all day.",
            ),
            dict(
                interruption_id="I2",
                scope="interval",
                datetime="2024-09-27T10:00:00+02:00/2024-09-27T12:00:00+02:00",
                time_precision="clock",
                effect="weather",
                note="Rain 10:00-12:00.",
            ),
        ]
    )
    survey = pd.DataFrame(
        [
            dict(
                survey_id="T1",
                datetime="2024-09-26T07:00:00Z/2024-09-26T15:00:00Z",
                recording_era="trektellen",
                weather="native",
                remark="unchanged",
            ),
            dict(
                survey_id="T2",
                datetime="2024-09-27T07:00:00Z/2024-09-27T09:00:00Z",
                recording_era="trektellen",
                weather="rain",
                remark="stopped",
            ),
            dict(
                survey_id="T3",
                datetime="2024-09-27T10:00:00Z/2024-09-27T11:00:00Z",
                recording_era="trektellen",
                weather="clear",
                remark="resumed",
            ),
        ]
    )
    counts = pd.DataFrame([dict(survey_id="T2", datetime="2024-09-27T07:30:00Z")])
    result, counts, _ = integrate_interruptions(survey, counts, events)
    rows = result.set_index("survey_id")
    assert rows.datetime.to_dict() == {
        "T3": "2024-09-27T10:00:00Z/2024-09-27T11:00:00Z",
        "T1": "2024-09-26T07:00:00Z/2024-09-26T15:00:00Z",  # a whole-day stop over a survey: no padding
        "T2": "2024-09-27T07:00:00Z/2024-09-27T08:00:00Z",
        "T2-weather": "2024-09-27T08:00:00Z/2024-09-27T09:00:00Z",
        "I2-weather": "2024-09-27T09:00:00Z/2024-09-27T10:00:00Z",
    }
    assert rows.weather_stop.to_dict() == {
        "T3": False,
        "T1": True,
        "T2": False,
        "T2-weather": True,
        "I2-weather": True,
    }
    assert rows.survey_complete.all()
    assert (
        rows.loc["T1", "survey_comment"] == "Rain all day."
        and rows.loc["I2-weather", "recording_era"] == "curated"
    )
    assert rows.loc["T2-weather", "remark"] == "stopped" and counts.survey_id.tolist() == ["T2"]


def test_inferred_workbook_day_links_report_without_duplicate_gap(tmp_path):
    events = pd.DataFrame(
        [
            dict(
                interruption_id="I1",
                scope="day",
                datetime="2008-09-04T00:00:00+02:00/2008-09-05T00:00:00+02:00",
                time_precision="day",
                effect="weather",
                note="inferred date",
            )
        ]
    )
    survey = pd.DataFrame(
        [
            dict(
                survey_id="H20080904-weather-day",
                datetime="2008-09-03T22:00:00Z/2008-09-04T22:00:00Z",
                recording_era="notebook",
                survey_complete=True,
                weather_stop=True,
                survey_comment="Weather stopped counting all day (report).",
            )
        ]
    )
    counts = pd.DataFrame(columns=["survey_id", "datetime"])
    result, _, _ = integrate_interruptions(survey, counts, events)
    assert len(result) == 1 and result.weather_stop.iloc[0] and result.survey_complete.iloc[0]


def test_historical_gaps_subtract_union_clip_window_and_cut_break():
    survey = pd.DataFrame(
        [
            dict(
                survey_id="H1",
                datetime="2018-08-17T07:00:00Z/2018-08-17T09:00:00Z",
                recording_era="naturalist",
            ),
            dict(
                survey_id="H2",
                datetime="2018-08-17T08:00:00Z/2018-08-17T09:00:00Z",
                recording_era="naturalist",
            ),
            dict(
                survey_id="H3",
                datetime="2018-08-17T13:30:00Z/2018-08-17T17:00:00Z",
                recording_era="naturalist",
            ),
        ]
    ).reindex(
        columns=[
            "survey_id",
            "datetime",
            "recording_era",
            "survey_complete",
            "weather_stop",
            "survey_comment",
            "remark_processing",
        ]
    )
    historical = pd.DataFrame(
        dict(
            sheet=["2017-2021"] * 2,
            date=pd.to_datetime(["2018-08-17"] * 2),
            day_start=pd.to_datetime(["2018-08-17T07:30:00Z"] * 2),
            day_end=pd.to_datetime(["2018-08-17T16:00:00Z"] * 2),
        )
    )
    breaks = pd.DataFrame(
        [
            dict(
                date="2018-08-17",
                datetime="2018-08-17T12:00:00+02:00/2018-08-17T15:30:00+02:00",
                note="Attendance break",
            )
        ]
    )
    result, audit = integrate_historical_gaps(survey, historical, breaks)
    pd.testing.assert_frame_equal(result.iloc[:3], survey, check_dtype=False)
    assert audit.hours.tolist() == [1, 3.5] and audit.status.tolist() == ["added", "cut"]
    assert len(result) == 4 and result.iloc[3].survey_complete and not result.iloc[3].weather_stop
    assert result.iloc[3].remark_processing == EMPTY_HOUR_NOTE
    assert result.iloc[3].datetime == "2018-08-17T09:00:00Z/2018-08-17T10:00:00Z"
    assert audit.note.iloc[1] == "Attendance break"
    # Rebuilding from the same declared windows cannot duplicate synthetic effort.
    again, audit = integrate_historical_gaps(result, historical, breaks)
    pd.testing.assert_frame_equal(again, result)
    assert audit.status.tolist() == ["cut"]
    # A count timed over the gap (09:00-10:00Z) shows counting then: no empty interval.
    count = pd.DataFrame(
        dict(
            count_id=["C1"],
            survey_id=["H1"],
            datetime=["2018-08-17T08:30:00Z/2018-08-17T10:30:00Z"],
        )
    )
    timed, audit = integrate_historical_gaps(survey, historical, breaks, count)
    assert len(timed) == 3 and audit.status.tolist() == ["cut"]


def test_historical_gaps_cover_edges_and_daily_surveys_leave_no_gap():
    survey = pd.DataFrame(
        [
            dict(
                survey_id="H1",
                datetime="2015-09-01T08:00:00Z/2015-09-01T09:00:00Z",
                recording_era="spreadsheet",
            ),
            dict(
                survey_id="H2",
                datetime="2013-09-01T07:00:00Z/2013-09-01T11:00:00Z",
                recording_era="notebook",
            ),
        ]
    ).reindex(
        columns=["survey_id", "datetime", "recording_era", "survey_complete", "remark_processing"]
    )
    historical = pd.DataFrame(
        dict(
            sheet=["2014-2016", "1966-2013"],
            date=pd.to_datetime(["2015-09-01", "2013-09-01"]),
            day_start=pd.to_datetime(["2015-09-01T07:30:00Z", "2013-09-01T07:00:00Z"]),
            day_end=pd.to_datetime(["2015-09-01T10:00:00Z", "2013-09-01T11:00:00Z"]),
        )
    )
    result, audit = integrate_historical_gaps(
        survey, historical, pd.DataFrame(columns=["date", "datetime", "note"])
    )
    assert audit.hours.tolist() == [0.5, 1]
    assert result.iloc[2:].recording_era.eq("spreadsheet").all()


def test_historical_gap_validation_detects_bounds_overlap_and_count_link():
    survey = pd.DataFrame(
        [
            dict(survey_id="N1", datetime="2019-08-20T05:00:00Z/2019-08-20T18:00:00Z"),
            dict(survey_id="N2", datetime="2019-08-20T17:00:00Z/2019-08-20T18:30:00Z"),
        ]
    )
    gaps = pd.DataFrame(
        dict(
            survey_id=["N1"],
            status=["added"],
            day_start=pd.to_datetime(["2019-08-20T05:35:00Z"]),
            day_end=pd.to_datetime(["2019-08-20T18:30:00Z"]),
        )
    )
    count = pd.DataFrame(
        dict(
            count_id=["C1", "C2", "C3"],
            survey_id=["N1", "N2", "N2"],
            # C2 is timed inside the gap although linked to another survey; C3 is a day total.
            datetime=["2019-08-20T06:00:00Z", "2019-08-20T10:00:00Z", "2019-08-20"],
        )
    )
    checks = validate_historical_gaps(survey, count, gaps)
    assert [check.status for check in checks] == ["fail", "fail", "fail"]
    assert [len(check.rows) for check in checks] == [1, 1, 2]
    assert set(checks[2].rows.count_id) == {"C1", "C2"}


def test_attendance_break_is_cut_not_counted_effort():
    survey = pd.DataFrame(
        [
            dict(
                survey_id="H1",
                datetime="2020-08-30T07:00:00Z/2020-08-30T08:00:00Z",
                recording_era="naturalist",
                survey_complete=True,
                weather_stop=False,
                remark_processing="",
                survey_comment="",
            )
        ]
    )
    historical = pd.DataFrame(
        dict(
            sheet=["2017-2021"],
            date=pd.to_datetime(["2020-08-30"]),
            day_start=pd.to_datetime(["2020-08-30T05:30:00Z"]),
            day_end=pd.to_datetime(["2020-08-30T08:00:00Z"]),
        )
    )
    breaks = pd.DataFrame(
        [
            dict(
                date="2020-08-30",
                datetime="2020-08-30T07:30:00+02:00/2020-08-30T09:00:00+02:00",
                note="Observers arrive later; no survey before.",
            )
        ]
    )
    result, gaps = integrate_historical_gaps(survey, historical, breaks)
    assert len(result) == 1 and gaps.status.tolist() == ["cut"]
    assert gaps.note.iloc[0] == breaks.note.iloc[0]


def test_empty_review_distinguishes_marker_missing_data_and_boundary_gap():
    survey = pd.DataFrame(
        [
            dict(
                survey_id="S1",
                source_survey_id="H1",
                datetime="2015-09-01T07:00:00Z/2015-09-01T08:00:00Z",
            ),
            dict(
                survey_id="S2",
                source_survey_id="H2",
                datetime="2015-09-01T08:00:00Z/2015-09-01T08:01:00Z",
            ),
            dict(
                survey_id="S3",
                source_survey_id="H3",
                datetime="2015-09-02T07:00:00Z/2015-09-02T08:00:00Z",
                survey_complete=False,
                remark_processing="No count entries; this does not establish species absences.",
                survey_comment="Known missing count data.",
            ),
            dict(
                survey_id="S4",
                source_survey_id="H4",
                datetime="2015-09-01T08:01:00Z/2015-09-01T09:00:00Z",
            ),
            dict(
                survey_id="S5",
                source_survey_id="H5",
                datetime="2015-09-03T07:00:00Z/2015-09-03T08:00:00Z",
                weather_stop=True,
                survey_comment="Rain all day.",
            ),
            dict(
                survey_id="S6",
                source_survey_id="H6",
                datetime="2015-09-04T07:00:00Z/2015-09-04T08:00:00Z",
                remark_processing="No count entries; this does not establish species absences.",
            ),
            dict(
                survey_id="S7",
                source_survey_id="H7",
                datetime="2015-09-05T07:00:00Z/2015-09-05T08:00:00Z",
                survey_complete=False,
                survey_comment="Birds passed while the observer was busy.",
            ),
        ]
    ).reindex(
        columns=[
            "survey_id",
            "source_survey_id",
            "datetime",
            "survey_complete",
            "weather_stop",
            "remark_processing",
            "recording_era",
            "survey_comment",
            "observers",
            "weather",
            "remark",
        ]
    )
    observations = pd.DataFrame([dict(survey_id="H1", taxon_kind="no_species")])
    count = pd.DataFrame([dict(survey_id="S4", datetime="2015-09-01")])
    gaps = pd.DataFrame(dict(source_survey_id=["H2"]))
    review = empty_survey_review(survey, count, observations, gaps).set_index("survey_id")
    assert review.review_class.to_dict() == {
        "S1": "explicit_no_species",
        "S2": "minute_boundary_gap",
        "S3": "missing_count_data",
        "S5": "weather_stop",
        "S6": "empty_native_header",
        "S7": "incomplete",
    }
    assert review.day_has_released_birds.to_dict() == {
        "S1": True,
        "S2": True,
        "S3": False,
        "S5": False,
        "S6": False,
        "S7": False,
    }


def test_incomplete_day_is_documented_status_in_coverage_context(tmp_path):
    folder = tmp_path / "config/audit-settings"
    folder.mkdir(parents=True)
    pd.DataFrame(
        [
            dict(
                start="2020-08-30",
                end="2020-08-30",
                reported_closure_days=1,
                partial_threshold_hours=None,
            )
        ]
    ).to_csv(folder / "report-season-windows.csv", index=False)
    pd.DataFrame(columns=["date", "note"]).to_csv(
        folder / "interruption-review-notes.csv", index=False
    )
    survey = pd.DataFrame(
        [
            dict(
                survey_id="Hgap",
                datetime="2020-08-30T05:30:00Z/2020-08-30T07:00:00Z",
                recording_era="naturalist",
                survey_complete=False,
                weather_stop=False,
                survey_comment="Attendance conflict",
            )
        ]
    )
    observations = pd.DataFrame(
        dict(
            date=pd.to_datetime([]), taxon_kind=pd.Series(dtype=str), count=pd.Series(dtype=float)
        )
    )
    review = interruption_review(survey, observations, tmp_path)
    assert review.assessment.tolist() == ["documented_incomplete"]
    assert review.incomplete.tolist() == [1]
    assert review.complete.tolist() == [0]
    assert review.weather_stop.tolist() == [0]
    assert review.note.tolist() == ["Attendance conflict"]
