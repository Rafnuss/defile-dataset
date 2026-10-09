"""Whole-row attribute assignments must not turn partial detail into extra birds."""

from pathlib import Path

import pandas as pd

from defile_dataset.attributes import (
    historical_attributes,
    quantity_components,
    split_historical_counts,
)

CROSSWALK = pd.read_csv(
    Path(__file__).resolve().parents[1] / "config/attributes/historical_attributes.csv", dtype=str
)


def test_attributes_keep_only_classes_supported_for_the_whole_count():
    hist = pd.DataFrame(
        {
            "sheet": ["2017-2021"] * 9,
            "row": range(2, 11),
            "date": pd.Timestamp("2020-09-15"),
            "count": [1, 3, 2, 3, 1, 1, 1, 1, 1],
            "details": [
                "1x mâle adulte",  # complete single class
                "1x mâle adulte / 2x femelle adulte",  # shared age, mixed sex
                "1x mâle adulte",  # only a subset described
                "1x adulte / 2x",  # unspecified birds prevent age assignment
                "1x mâle > 1 an",  # age lower bound, adult status unspecified
                "1x type femelle",  # female-coloured does not mean female
                "1x 1ère année civile (en vol)",  # retain calendar age, ignore flight annotation
                "peut-être adulte",  # avoid speculative keyword extraction
                "1x stade nouveau",  # unmapped vocabulary stays unassigned
            ],
        }
    )
    original = hist.copy(deep=True)
    values, audit = historical_attributes(hist, CROSSWALK)
    assert values.loc[0, ["age", "sex"]].tolist() == ["A", "M"]
    assert values.loc[1, "age"] == "A" and pd.isna(values.loc[1, "sex"])
    assert values.loc[[2, 3], ["age", "sex", "plumage"]].isna().all().all()
    assert values.loc[4, "sex"] == "M" and values.loc[4, "age"] == ">1y"
    assert values.loc[5, "sex"] == "FC"
    assert values.loc[6, "age"] == "1"
    assert values.loc[[7, 8], ["age", "sex", "plumage"]].isna().all().all()
    assert audit.loc[2, "status"] == "mapped"
    assert audit.loc[7, "status"] == "unparsed"
    pd.testing.assert_frame_equal(hist, original)
    assert audit["count"].sum() == hist["count"].sum()


def test_historical_immature_uses_documented_local_age_assumption():
    hist = pd.DataFrame(
        {
            "sheet": ["2014-2016", "2017-2021", "1966-2013"],
            "row": [2, 2, 2],
            "date": pd.Timestamp("2015-09-15"),
            "count": [1, 1, 5],
            "detail": ["1x mâle immature", None, None],
            "details": [None, "1x immature", None],
        }
    )
    values, audit = historical_attributes(hist, CROSSWALK)
    assert values.loc[:1, "age"].tolist() == ["I", "I"]
    assert values.loc[:1, "remark_processing"].str.contains("Assumed local convention").all()
    assert values.loc[0, "sex"] == "M"
    assert len(audit) == 2
    assert values.loc[2].isna().all()


def test_adult_female_type_and_unspecified_groups_do_not_require_review():
    hist = pd.DataFrame(
        dict(
            sheet=["1966-2013", "2014-2016"] + ["2017-2021"] * 7,
            row=range(2, 11),
            date=pd.Timestamp("2020-09-15"),
            count=[1, 1, 1, 1, 1, 2, 3, 1, 1],
            detail=["1x type femelles adultes", "1x type femelles adultes"] + [None] * 7,
            details=[
                None,
                None,
                "1x type femelle adulte",
                "1x (entendu)",
                "1x (en vol)",
                "2x",
                "1x adulte / 2x (entendu)",
                "1x stade nouveau",
                "2x (entendu)",
            ],
        )
    )
    values, audit = historical_attributes(hist, CROSSWALK)
    assert values.loc[:2, "age"].eq("A").all()
    assert values.loc[:2, "sex"].eq("FC").all()
    assert values.loc[3:6, ["age", "sex", "plumage"]].isna().all().all()
    assert audit.status.tolist() == ["mapped"] * 7 + ["unassigned", "quantity_mismatch"]
    released = split_historical_counts(
        hist.join(values).assign(observation_id=audit.observation_id), quantity_components(audit)
    )
    assert pd.isna(released.details.iloc[2])
    assert released.details.iloc[3] == "(entendu)"
    assert released.details.iloc[7] == "(entendu)"
    assert released["count"].sum() == hist["count"].sum()


def test_imported_notebook_details_use_the_same_whole_row_policy():
    hist = pd.DataFrame(
        {
            "sheet": ["1966-2013"] * 3,
            "row": [2, 3, 4],
            "date": pd.Timestamp("2012-09-15"),
            "count": [3, 12, 1],
            "detail": [
                "1x mâle adulte / 2x femelles adultes",
                "4x adultes",
                "1x type femelle immature",
            ],
        }
    )
    values, audit = historical_attributes(hist, CROSSWALK)
    assert values.loc[0, "age"] == "A" and pd.isna(values.loc[0, "sex"])
    assert values.loc[1, ["age", "sex", "plumage"]].isna().all()
    assert audit.loc[1, "status"] == "mapped"
    assert values.loc[2, ["age", "sex"]].tolist() == ["I", "FC"]


def test_subgroups_remainder_unknown_zero_and_conflict_preserve_source_counts():
    hist = pd.DataFrame(
        dict(
            sheet=["2017-2021"] * 5,
            row=range(2, 7),
            date=pd.Timestamp("2020-09-15"),
            count=[5, 3, 2, 2, 2],
            details=[
                "1x mâle adulte / 2x femelle adulte",
                "1x mâle adulte / 2x stade nouveau",
                "0x mâle adulte / 2x femelle adulte",
                "3x adulte",
                "texte non structuré",
            ],
        )
    )
    values, audit = historical_attributes(hist, CROSSWALK)
    source = hist.join(values).assign(observation_id=audit.observation_id)
    original = source.copy(deep=True)
    parts = quantity_components(audit)
    released = split_historical_counts(source, parts)
    first = released[released.observation_id.str.startswith("H-2017-2021-r2")]
    assert first["count"].tolist() == [1, 2, 2]
    assert first.age.iloc[:2].tolist() == ["A", "A"] and pd.isna(first.age.iloc[2])
    assert first.sex.iloc[:2].tolist() == ["M", "F"] and pd.isna(first.sex.iloc[2])
    assert first.observation_id.tolist() == [
        "H-2017-2021-r2-part1",
        "H-2017-2021-r2-part2",
        "H-2017-2021-r2-part3",
    ]
    unknown = released[released.observation_id.eq("H-2017-2021-r3-part2")].iloc[0]
    assert pd.isna(unknown.age) and pd.isna(unknown.sex) and unknown["count"] == 2
    assert released.loc[released.observation_id.eq("H-2017-2021-r4"), "sex"].iloc[0] == "F"
    assert released.loc[released.observation_id.eq("H-2017-2021-r5"), "count"].iloc[0] == 2
    assert released.loc[released.observation_id.eq("H-2017-2021-r6"), "count"].iloc[0] == 2
    totals = (
        released["count"]
        .groupby(released.observation_id.str.replace(r"-part\d+$", "", regex=True))
        .sum()
    )
    assert totals.to_dict() == source.set_index("observation_id")["count"].to_dict()
    pd.testing.assert_frame_equal(source, original)


def test_immature_and_first_year_subgroups_keep_distinct_ages():
    hist = pd.DataFrame(
        dict(
            sheet=["2017-2021"],
            row=[65504],
            date=pd.Timestamp("2021-09-01"),
            count=[11],
            details=["5x immatures / 1x 1ère année civile / 5x adultes"],
        )
    )
    values, audit = historical_attributes(hist, CROSSWALK)
    source = hist.join(values).assign(observation_id=audit.observation_id)
    released = split_historical_counts(source, quantity_components(audit))
    assert released.age.tolist() == ["I", "1", "A"]
    assert released["count"].tolist() == [5, 1, 5]
    assert released["count"].sum() == hist["count"].sum()
    assert released.remark_processing.str.contains("Assumed local convention").all()


def test_published_daily_context_preserves_recorded_attributes_and_subgroups():
    hist = pd.DataFrame(
        dict(
            sheet=["2017-2021", "1966-2013", "2014-2016"],
            row=[2, 2, 2],
            date=pd.Timestamp("2020-09-15"),
            count=[3, 1, 1],
            details=["1x mâle adulte / 2x femelle adulte", None, None],
            detail=[None, "1x adulte", None],
        )
    )
    expected_values, expected_audit = historical_attributes(hist, CROSSWALK)
    annotated = hist.copy(deep=True)
    annotated.loc[
        0, "details"
    ] += "\n\n[Rapport annuel 2020; Contexte journalier 2020-09-15, Busard pâle; non attribué à cette tranche horaire] 7 mâles adultes ont passé."
    annotated.loc[
        1, "detail"
    ] += "\n\n[Nos Oiseaux 1996-I; Contexte journalier 1993-09-15, Busard pâle] Un mâle adulte."
    annotated.loc[
        2, "detail"
    ] = "[Rapport annuel 2015; Contexte journalier 2015-09-15, Busard pâle] Un mâle adulte."
    values, audit = historical_attributes(annotated, CROSSWALK)
    pd.testing.assert_frame_equal(values, expected_values)
    pd.testing.assert_frame_equal(audit, expected_audit)
    pd.testing.assert_frame_equal(quantity_components(audit), quantity_components(expected_audit))
    assert annotated.loc[0, "details"].endswith("7 mâles adultes ont passé.")


def test_released_details_keep_only_unconverted_information_and_published_context():
    hist = pd.DataFrame(
        dict(
            sheet=["2017-2021"] * 3,
            row=[2, 3, 4],
            date=pd.Timestamp("2020-09-15"),
            count=[3, 1, 1],
            details=["1x mâle adulte / 2x femelle adulte", "1x mâle > 1 an", "1x mâle immature"],
        )
    )
    context = "[Rapport annuel 2020; Contexte journalier 2020-09-15, Milan royal; non attribué à cette tranche horaire] Un grand passage."
    hist.loc[0, "details"] += "\n\n" + context
    values, audit = historical_attributes(hist, CROSSWALK)
    source = hist.join(values).assign(observation_id=audit.observation_id)
    released = split_historical_counts(source, quantity_components(audit))
    assert released.details.iloc[:2].eq(context).all()
    assert pd.isna(released.details.iloc[2]) and released.age.iloc[2] == ">1y"
    assert pd.isna(released.details.iloc[3])
    assert released.remark_processing.iloc[3].startswith("Assumed local convention:")
    assert not released.remark_processing.fillna("").str.contains("Component|Source H-").any()
    assert source.details.iloc[0].startswith("1x mâle adulte")
