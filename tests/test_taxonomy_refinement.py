"""Owner-reviewed taxonomy changes preserve source quantities and independent attributes."""

import pandas as pd

from defile_dataset.taxonomy_refinement import refine_taxonomy


def records(text="dont 10 Grive sp.", count=25):
    normal = pd.DataFrame(
        [
            dict(
                observation_id="H1",
                source_count_id="H1",
                source="historical",
                taxon_name_original="Grive musicienne",
                avibase_id="song",
                count=count,
                comment=text,
                comment_residual=text,
                age=None,
                sex=None,
                plumage=None,
                datetime=pd.NaT,
                detail=None,
                details=None,
                remark_processing=None,
            )
        ]
    )
    rule = pd.DataFrame(
        [
            dict(
                decision="approve",
                review_id="rule",
                review_group="group",
                source_taxon="Grive musicienne",
                source_field="comment",
                source_text=text,
                scope="subset_requires_split",
                target_taxon_id="turdus",
                consume_text=True,
            )
        ]
    )
    return normal, rule


def test_taxonomy_subset_changes_only_explicit_birds_and_preserves_source():
    normal, rules = records()
    original = normal.copy(deep=True)
    result, audit = refine_taxonomy(normal, rules)
    assert result["count"].tolist() == [10, 15]
    assert result.taxon_id.tolist() == ["turdus", "song"]
    assert result.source_count_id.eq("H1").all() and result.avibase_id.eq("song").all()
    assert result.comment_residual.isna().all() and audit.status.eq("applied").all()
    pd.testing.assert_frame_equal(normal, original)


def test_age_totals_do_not_imply_which_taxon_subset_was_aged():
    normal, rules = records()
    normal = pd.concat([normal, normal], ignore_index=True)
    normal["count"] = [10, 15]
    normal["age"] = ["A", "1"]
    result, audit = refine_taxonomy(normal, rules)
    assert result.taxon_id.eq("song").all() and result["count"].sum() == 25
    assert result.comment_residual.eq("dont 10 Grive sp.").all()
    assert audit.status.eq("unassociated_attribute_or_time_subgroups").all()


def test_whole_taxon_mapping_preserves_age_groups_and_specific_text_if_target_is_broad():
    normal, rules = records("Grive sp.")
    rules["scope"] = "whole_count_candidate"
    rules["consume_text"] = False
    result, _ = refine_taxonomy(normal, rules)
    assert result.taxon_id.eq("turdus").all()
    assert result.comment_residual.eq("Grive sp.").all() and result["count"].sum() == 25


def test_conflicting_reviewed_targets_leave_the_identification_unchanged():
    normal, rules = records()
    other = rules.assign(review_id="other", target_taxon_id="another")
    result, audit = refine_taxonomy(normal, pd.concat([rules, other]))
    assert result.taxon_id.eq("song").all()
    assert result.comment_residual.eq("dont 10 Grive sp.").all()
    assert audit.status.eq("conflicting_taxonomy_rules").all()
