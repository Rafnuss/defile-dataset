"""Residual text conversions retain scope, precision and conflicting source wording."""

import pandas as pd
import pytest

from defile_dataset.remark_text import clean_text, convert_remark_text, timing_phrase


def records(remark, age=None, datetime="2024-11-04"):
    count = pd.DataFrame(
        [
            dict(
                count_id="T1-normal",
                source_count_id="T1",
                survey_id="S1",
                count_category="normal",
                count=3,
                age=age,
                datetime=datetime,
                remark=remark,
                remark_processing=None,
            )
        ]
    )
    survey = pd.DataFrame(
        [dict(survey_id="S1", datetime="2024-11-04T06:00:00Z/2024-11-04T17:00:00Z")]
    )
    return count, survey


def test_whitespace_and_empty_remarks():
    assert (
        clean_text(pd.Series([" \n\t\u00a0", " text\r\nsecond line  "])).tolist()[1]
        == "text\nsecond line"
    )
    assert pd.isna(clean_text(pd.Series([" \n\t\u00a0"])).iloc[0])


@pytest.mark.parametrize(
    "remark,code,remaining",
    [
        ("imm", "I", None),
        ("imm.", "I", None),
        ("Im.", "I", None),
        ("Immatures. NPP", "I", "NPP"),
        ("> 1 an", ">1y", None),
        ("immature\npossiblement un oiseau relâché", "I", "possiblement un oiseau relâché"),
    ],
)
def test_attribute_text_is_consumed_only_when_converted(remark, code, remaining):
    count, survey = records(remark)
    result, audit = convert_remark_text(count, survey)
    assert result.age.iloc[0] == code
    assert (
        pd.isna(result.remark.iloc[0]) if remaining is None else result.remark.iloc[0] == remaining
    )
    assert audit.converted.iloc[0] == "age"
    assert count.remark.iloc[0] == remark


def test_attribute_conflict_preserves_wording_and_existing_code():
    count, survey = records("imm.", age="2")
    result, audit = convert_remark_text(count, survey)
    assert result.age.iloc[0] == "2" and result.remark.iloc[0] == "imm."
    assert "Age text conflict" in result.remark_processing.iloc[0]
    assert audit.converted.iloc[0] == ""


def test_two_competing_clocks_do_not_silently_overwrite_each_other():
    count, survey = records("1200 | 13h")
    result, _ = convert_remark_text(count, survey)
    assert result.datetime.iloc[0] == "2024-11-04T11:00:00Z"
    assert result.remark.iloc[0] == "13h"
    assert "conflicts with existing datetime" in result.remark_processing.iloc[0]


def test_subgroup_quantity_does_not_establish_which_flock_was_aged():
    count, survey = records("4 à 12h35 - 17 à 12h50")
    count = pd.concat([count, count], ignore_index=True)
    count["count"] = [4, 17]
    count["age"] = ["A", "1"]
    result, audit = convert_remark_text(count, survey)
    assert result.datetime.eq("2024-11-04").all()
    assert result.remark.eq("4 à 12h35 - 17 à 12h50").all() and audit.empty


def test_repeated_native_age_text_is_removed_for_other_categories_without_inferring_new_ages():
    count, survey = records("imm.", age="I")
    count["count_category"] = "local"
    result, _ = convert_remark_text(count, survey)
    assert pd.isna(result.remark.iloc[0]) and result.age.iloc[0] == "I"
    count["age"] = None
    result, _ = convert_remark_text(count, survey)
    assert result.remark.iloc[0] == "imm." and pd.isna(result.age.iloc[0])


@pytest.mark.parametrize(
    "remark,expected",
    [
        ("1200", "2024-11-04T11:00:00Z"),
        ("à 12h", "2024-11-04T11:00:00Z"),
        ("9-10h", "2024-11-04T08:00:00Z/2024-11-04T09:00:00Z"),
        ("de 11h15 à 11h45", "2024-11-04T10:15:00Z/2024-11-04T10:45:00Z"),
    ],
)
def test_points_and_ranges_use_utc_without_midpoint_invention(remark, expected):
    count, survey = records(remark)
    result, audit = convert_remark_text(count, survey)
    assert result.datetime.iloc[0] == expected and pd.isna(result.remark.iloc[0])
    assert audit.converted.iloc[0] == "datetime"


def test_range_preserves_more_precise_timestamp_and_conflicts_remain():
    count, survey = records("9-10h", datetime="2024-11-04T08:30:12Z")
    result, _ = convert_remark_text(count, survey)
    assert result.datetime.iloc[0] == count.datetime.iloc[0] and pd.isna(result.remark.iloc[0])
    count, survey = records("1200", datetime="2024-11-04T12:00:00Z")
    result, _ = convert_remark_text(count, survey)
    assert result.datetime.iloc[0] == count.datetime.iloc[0] and result.remark.iloc[0] == "1200"
    assert "conflicts with existing datetime" in result.remark_processing.iloc[0]


def test_published_context_and_uncertainty_stay_but_explicit_outside_clock_is_retained():
    context = "[Rapport annuel 2024; Contexte journalier 2024-11-04, Milan noir] immatures à 12h"
    count, survey = records(context)
    result, audit = convert_remark_text(count, survey)
    assert result.remark.iloc[0] == context and audit.empty
    for text in [
        "vers 12h",
        "Après 2h30 de suivi",
        "immature probable",
        "1 immature et 2 adultes",
        "2500",
    ]:
        assert timing_phrase(text, 3) is None
    count, survey = records("immature probable")
    result, _ = convert_remark_text(count, survey)
    assert pd.isna(result.age.iloc[0]) and result.remark.iloc[0] == "immature probable"
    count, survey = records("à 20h")
    result, _ = convert_remark_text(count, survey)
    assert (
        pd.isna(result.remark.iloc[0])
        and result.datetime.iloc[0] == "2024-11-04T19:00:00Z"
        and "outside linked survey" in result.remark_processing.iloc[0]
    )
    assert survey.datetime.iloc[0] == "2024-11-04T06:00:00Z/2024-11-04T17:00:00Z"
