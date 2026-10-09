"""Survey status: complete by default, weather stops complete with no bird, absences cut; every bird record kept."""
import pandas as pd
import pytest

from defile_dataset.survey_review import integrate_interruptions, observed_hours
from defile_dataset.survey_status import (
    classify_trektellen,
    parse_tag,
    read_reviewed_status,
    release_status,
)


def native(remark="", birds=True):
    surveys = pd.DataFrame(
        [
            dict(
                survey_id="T1",
                source="trektellen",
                trektellen_count_id=1,
                date=pd.Timestamp("2027-08-01"),
                start=pd.Timestamp("2027-08-01T06:00Z"),
                end=pd.Timestamp("2027-08-01T16:00Z"),
                start_original=pd.Timestamp("2027-08-01T06:00Z"),
                end_original=pd.Timestamp("2027-08-01T16:00Z"),
                weather="",
                remarks=remark,
            )
        ]
    )
    observations = (
        pd.DataFrame(
            [
                dict(
                    survey_id="T1",
                    taxon_kind="bird",
                    datetime=pd.Timestamp("2027-08-01T07:00Z"),
                    count=5,
                )
            ]
        )
        if birds
        else pd.DataFrame(columns=["survey_id", "taxon_kind", "datetime", "count"])
    )
    return surveys, observations, read_reviewed_status(".").iloc[:0]


def reviewed(**row):
    return pd.DataFrame(
        [
            dict(
                decision_id="I1",
                count_id="1",
                scope="period",
                datetime="",
                time_precision="clock",
                survey_complete="",
                weather_stop="",
                survey_comment="",
                native_weather="",
                native_remarks="",
            )
            | row
        ]
    )


def released(result):
    return result.assign(
        datetime="2027-08-01T06:00:00Z/2027-08-01T16:00:00Z", recording_era="trektellen"
    )


@pytest.mark.parametrize(
    "body, expected",
    [
        ("weather", ("weather", None, None)),
        ("weather from=10:00 to=12:30", ("weather", "10:00", "12:30")),
        ("absent from=12:00 to=13:30", ("absent", "12:00", "13:30")),
        ("incomplete", ("incomplete", None, None)),
        ("survey_coverage=none reason=weather", ("weather", None, None)),
        ("survey_coverage=none", ("weather", None, None)),
        (
            "survey_coverage=none reason=logistics from=10:00 to=12:00",
            ("absent", "10:00", "12:00"),
        ),
        ("survey_coverage=none reason=no_observer", ("remove", None, None)),
        ("survey_coverage=partial", ("complete", None, None)),
        ("survey_coverage=unknown", ("incomplete", None, None)),
    ],
)
def test_tags_new_and_legacy(body, expected):
    assert parse_tag(body) == expected


def test_empty_header_is_complete_and_hp_text_is_reviewed():
    result, intervals, review = classify_trektellen(*native("HP brouillard", birds=False))
    assert result.survey_complete.iloc[0] and not result.weather_stop.iloc[0] and intervals.empty
    assert set(review.issue) == {"ambiguous_status_text"}


def test_whole_day_weather_stop_and_birds_contradicting_it():
    s, o, r = native("[DEFILE weather] Pluie toute la journée.", birds=False)
    result, intervals, review = classify_trektellen(s, o, r)
    assert (
        result.survey_complete.iloc[0]
        and result.weather_stop.iloc[0]
        and review.empty
        and intervals.empty
    )
    _, birds, _ = native()
    before = birds.copy(deep=True)
    result, _, review = classify_trektellen(s, birds, r)
    assert result.survey_complete.iloc[0] and not result.weather_stop.iloc[0]
    assert "birds_in_weather_stop" in set(review.issue)
    pd.testing.assert_frame_equal(birds, before)


def test_incomplete_is_listed_with_its_comment():
    s, o, _ = native()
    result, _, review = classify_trektellen(
        s, o, reviewed(survey_complete="false", survey_comment="Records lost.")
    )
    assert not result.survey_complete.iloc[0] and result.survey_comment.iloc[0] == "Records lost."
    assert review.loc[review.issue.eq("incomplete_survey"), "detail"].tolist() == ["Records lost."]


def test_removal_drops_an_empty_header_but_never_one_with_birds():
    s, o, r = native("[DEFILE survey_coverage=none reason=no_observer]", birds=False)
    result, _, review = classify_trektellen(s, o, r)
    assert result.empty and review.empty
    _, birds, _ = native()
    result, _, review = classify_trektellen(s, birds, r)
    assert len(result) == 1 and "removal_with_birds" in set(review.issue)


def test_missing_original_hours_are_listed():
    s, o, r = native("[DEFILE weather]", birds=False)
    s[["start_original", "end_original"]] = pd.NaT
    assert "missing_survey_hours" in set(classify_trektellen(s, o, r)[2].issue)


def test_changed_source_withholds_decision_even_with_birds():
    s, o, _ = native("new wording")
    result, intervals, review = classify_trektellen(
        s, o, reviewed(weather_stop="true", native_remarks="old wording")
    )
    assert result.survey_complete.iloc[0] and not result.weather_stop.iloc[0] and intervals.empty
    assert "reviewed_source_changed" in set(review.issue)


def test_conflicting_whole_header_tags_are_withheld():
    result, intervals, review = classify_trektellen(
        *native("[DEFILE weather] [DEFILE incomplete]", birds=False)
    )
    assert result.survey_complete.iloc[0] and not result.weather_stop.iloc[0] and intervals.empty
    assert "conflicting_classification" in set(review.issue)


def test_timed_weather_stop_splits_the_header_into_its_own_row(tmp_path):
    s, o, r = native("[DEFILE weather from=10:00 to=12:30] Pluie.")
    result, intervals, review = classify_trektellen(s, o, r)
    assert review.empty and intervals.effect.tolist() == ["weather"]
    count = pd.DataFrame(
        dict(
            count_id=["C1", "C2"], survey_id=["T1", "T1"], datetime=["2027-08-01T07:00:00Z", pd.NA]
        )
    )
    survey, count, _ = integrate_interruptions(released(result), count, tmp_path, intervals)
    rows = survey.set_index("survey_id")
    assert rows.datetime.to_dict() == {
        "T1": "2027-08-01T06:00:00Z/2027-08-01T08:00:00Z",
        "T1-part2": "2027-08-01T10:30:00Z/2027-08-01T16:00:00Z",
        "T1-weather": "2027-08-01T08:00:00Z/2027-08-01T10:30:00Z",
    }
    assert rows.weather_stop.tolist() == [False, False, True] and rows.survey_complete.all()
    assert count.survey_id.tolist() == ["T1", "T1"] and count.datetime.tolist() == [
        "2027-08-01T07:00:00Z",
        "2027-08-01",
    ]
    hours = survey.assign(
        start=pd.to_datetime(survey.datetime.str.split("/").str[0]),
        end=pd.to_datetime(survey.datetime.str.split("/").str[1]),
    )
    assert observed_hours(hours) == 7.5


def test_absence_is_cut_and_its_counts_follow_their_times(tmp_path):
    s, o, r = native("[DEFILE absent from=10:00 to=12:00]")
    result, intervals, review = classify_trektellen(s, o, r)
    count = pd.DataFrame(
        dict(
            count_id=["C1", "C2"],
            survey_id=["T1", "T1"],
            datetime=["2027-08-01T07:00:00Z", "2027-08-01T13:00:00Z"],
        )
    )
    survey, count, _ = integrate_interruptions(released(result), count, tmp_path, intervals)
    assert survey.survey_id.tolist() == ["T1", "T1-part2"] and not survey.weather_stop.any()
    assert count.survey_id.tolist() == ["T1", "T1-part2"]


def test_untimed_birds_near_an_interruption_are_listed():
    s, o, r = native("[DEFILE weather from=10:00 to=12:30]")
    o.datetime = pd.NaT
    result, intervals, review = classify_trektellen(s, o, r)
    assert "untimed_birds_near_interruption" in set(review.issue) and o["count"].sum() == 5


def test_weather_after_the_header_is_a_curated_row(tmp_path):
    s, o, _ = native()
    result, intervals, review = classify_trektellen(
        s,
        o,
        reviewed(
            scope="interval",
            datetime="2027-08-01T16:00Z/2027-08-01T18:00Z",
            time_precision="bounded",
            weather_stop="true",
            survey_comment="Rain after the session.",
        ),
    )
    assert (
        review.empty and result.survey_complete.iloc[0] and pd.isna(result.survey_comment.iloc[0])
    )
    count = pd.DataFrame(
        dict(count_id=["C1"], survey_id=["T1"], datetime=["2027-08-01T07:00:00Z"])
    )
    survey, count, _ = integrate_interruptions(released(result), count, tmp_path, intervals)
    assert survey.recording_era.tolist() == [
        "trektellen",
        "curated",
    ] and survey.weather_stop.tolist() == [False, True]
    assert survey.survey_comment.iloc[
        1
    ] == "Rain after the session." and count.survey_id.tolist() == ["T1"]


def test_release_writes_true_false_and_blank():
    out = release_status(
        pd.DataFrame(dict(survey_complete=[True, False, True], weather_stop=[False, False, True]))
    )
    assert out.survey_complete.tolist() == ["true", "false", "true"]
    assert out.weather_stop.isna().tolist() == [True, True, False]
