"""Non-passage wording changes category without duplicating birds or interpreting narratives."""

import pandas as pd
import pytest

from defile_dataset.movement_text import project_non_passage


@pytest.mark.parametrize("remark", ["npp", " NNP. ", "ne passe pas", "N.P.P."])
def test_standalone_non_passage_transfers_quantity_and_preserves_source(remark):
    source = pd.DataFrame(
        [dict(observation_id="T1", count=10, local=0, direction2=0, remark=remark)]
    )
    original = source.copy(deep=True)
    result, audit = project_non_passage(source)
    assert result["count"].iloc[0] == 0 and result.local.iloc[0] == 10
    assert pd.isna(result.remark.iloc[0]) and audit.status.iloc[0] == "moved_to_local"
    pd.testing.assert_frame_equal(source, original)


def test_already_local_consumes_only_explicit_standalone_wording():
    source = pd.DataFrame(
        [dict(observation_id="T1", count=0, local=6, direction2=0, remark="NPP")]
    )
    result, audit = project_non_passage(source)
    assert result.local.iloc[0] == 6 and pd.isna(result.remark.iloc[0])
    assert audit.status.iloc[0] == "already_local"


@pytest.mark.parametrize(
    "remark", ["npp?", "3 NPP et 1 loc", "Un héron ne passe pas; groupe détecté grâce à lui."]
)
def test_uncertain_subset_and_companion_text_stays(remark):
    source = pd.DataFrame(
        [dict(observation_id="T1", count=10, local=0, direction2=0, remark=remark)]
    )
    result, audit = project_non_passage(source)
    assert result["count"].iloc[0] == 10 and result.remark.iloc[0] == remark and audit.empty


def test_conflicting_native_categories_stay_and_are_audited():
    source = pd.DataFrame(
        [dict(observation_id="T1", count=10, local=2, direction2=0, remark="NPP")]
    )
    result, audit = project_non_passage(source)
    assert (
        result["count"].iloc[0] == 10
        and result.local.iloc[0] == 2
        and result.remark.iloc[0] == "NPP"
    )
    assert audit.status.iloc[0] == "conflicting_or_unquantified"


@pytest.mark.parametrize("marker", ["loc", "LOC.", "H", "Halte", "en halte"])
def test_local_marker_overrides_main_and_reverse_with_total_preserved(marker):
    source = pd.DataFrame(
        [dict(observation_id="T1", count=4, direction2=3, local=2, remark=marker)]
    )
    result, audit = project_non_passage(source)
    assert result[["count", "direction2", "local"]].iloc[0].tolist() == [0, 0, 9]
    assert pd.isna(result.remark.iloc[0]) and audit.status.iloc[0] == "local_override"


def test_local_marker_in_comment_is_consumed_without_removing_other_remark():
    source = pd.DataFrame(
        [
            dict(
                observation_id="H1",
                count=4,
                direction2=None,
                local=None,
                comment="Halte",
                comment_residual="Halte",
                remark="posé sur le Rhône",
            )
        ]
    )
    result, _ = project_non_passage(source)
    assert result.local.iloc[0] == 4 and result["count"].iloc[0] == 0
    assert pd.isna(result.comment.iloc[0]) and pd.isna(result.comment_residual.iloc[0])
    assert result.remark.iloc[0] == "posé sur le Rhône"
