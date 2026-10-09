"""Reviewed clocks must not change quantities or be restored from rejected source text."""

import pandas as pd

from defile_dataset.remark_text import convert_remark_text
from defile_dataset.timing_review import reviewed_entry_times


def test_clear_interval_and_relink_preserve_original_evidence_and_quantities():
    rows = pd.DataFrame(
        {
            "observation_id": ["T1", "H1", "H2", "T2"],
            "survey_id": ["S1"] * 4,
            "date": pd.to_datetime(["2021-11-06"] * 4),
            "source": ["trektellen", "historical", "historical", "trektellen"],
            "taxon_name_original": ["Milan royal"] * 4,
            "count": [517, 12, 1, 8],
            "local": [0, 0, 0, 2],
            "direction2": [0] * 4,
            "datetime": pd.to_datetime(["2021-11-06T17:27:00Z"] * 4),
            "datetime_original": pd.to_datetime(["2021-11-06T17:27:00Z"] * 4),
            "time_resolution": ["point"] * 4,
            "flags": ["", "", "time_outside_survey", ""],
            "comment": [None, "à 18h27", "à 16h29", None],
            "remark": [None] * 4,
            "use_for_counts": [True, True, True, False],
        }
    )
    original = rows.copy(deep=True)
    decisions = (
        pd.DataFrame(
            [
                dict(
                    observation_id="T1",
                    action="clear",
                    reason="Rejected entry clock.",
                    evidence="review",
                ),
                dict(
                    observation_id="H1",
                    action="interval",
                    interval_start="2021-11-06T06:00:00Z",
                    interval_end="2021-11-06T16:30:00Z",
                    reason="Documented daily bounds.",
                    evidence="workbook",
                ),
                dict(
                    observation_id="H2",
                    action="point",
                    datetime="2021-11-06T15:29:00Z",
                    survey_id="S2",
                    reason="Explicit clock and corrected link.",
                    evidence="comment",
                ),
            ]
        )
        .reindex(
            columns=[
                "observation_id",
                "action",
                "date",
                "datetime",
                "interval_start",
                "interval_end",
                "survey_id",
                "reason",
                "evidence",
            ]
        )
        .fillna("")
    )
    decisions["date"] = "2021-11-06"
    corrected, audit = reviewed_entry_times(
        rows, pd.DataFrame({"survey_id": ["S1", "S2"]}), decisions
    )
    pd.testing.assert_frame_equal(rows, original)
    pd.testing.assert_frame_equal(
        corrected[["count", "local", "direction2", "use_for_counts", "datetime_original"]],
        original[["count", "local", "direction2", "use_for_counts", "datetime_original"]],
    )
    assert pd.isna(corrected.loc[0, "datetime"]) and pd.isna(corrected.loc[0, "datetime_interval"])
    assert (
        corrected.loc[0, "survey_id"] == "S1" and corrected.loc[0, "time_resolution"] == "interval"
    )
    assert corrected.loc[1, "datetime_interval"] == "2021-11-06T06:00:00Z/2021-11-06T16:30:00Z"
    assert corrected.loc[2, "datetime"] == pd.Timestamp("2021-11-06T15:29:00Z")
    assert corrected.loc[2, "survey_id"] == "S2" and corrected.loc[2, "survey_id_original"] == "S1"
    assert "time_outside_survey" not in corrected.loc[2, "flags"]
    assert corrected.loc[3, "datetime"] == original.loc[3, "datetime"]
    assert len(audit) == 3 and audit["count"].sum() == 530


def test_remark_processing_does_not_restore_a_rejected_clock():
    count = pd.DataFrame(
        [
            dict(
                count_id="C1",
                source_count_id="H1",
                survey_id="S1",
                count_category="normal",
                count=517,
                age=None,
                datetime=None,
                remark="à 18h27",
                remark_processing="Reviewed timing: unsupported closing tally.",
            )
        ]
    )
    survey = pd.DataFrame(
        [dict(survey_id="S1", datetime="2021-11-06T06:00:00Z/2021-11-06T16:30:00Z")]
    )
    corrected, _ = convert_remark_text(count, survey)
    assert pd.isna(corrected.loc[0, "datetime"])
    assert corrected.loc[0, "remark"] == "à 18h27"
