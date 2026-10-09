"""Taxonomy clues need identification and quantity scope, not just a species mention."""

from defile_dataset.taxonomy_text import identify_clue, normalize_text, taxon_phrase

ALIASES = {"mesanges": {"proposed_taxon_id": "parid"}, "grive sp": {"proposed_taxon_id": "turdus"}}


def test_spelling_and_quantities_preserve_whole_vs_partial_scope():
    assert normalize_text("  Mésanges. ") == "mesanges"
    assert taxon_phrase("6xmesanges") == ("mesanges", 6, False)
    assert identify_clue("10 x mésanges", ALIASES, 10)[1:] == ("whole_count_candidate", 10)
    assert identify_clue("10 x mésanges", ALIASES, 20)[1:] == ("subset_requires_split", 10)
    assert identify_clue("dont 10 Grive sp.", ALIASES, 20)[1:] == ("subset_requires_split", 10)
    assert identify_clue("10 x mésanges", ALIASES, 3)[1] == "quantity_exceeds_source"


def test_mentions_and_published_context_never_become_exact_identifications():
    assert identify_clue("Avec 6 Grandes Aigrettes.", ALIASES, 1)[0] is None
    assert identify_clue("Probable mésange", ALIASES, 1)[0] is None
    assert (
        identify_clue(
            "[Rapport annuel 2020; Contexte journalier 2020-09-15, X] mésanges", ALIASES, 1
        )[1]
        == "no_taxonomy_clue"
    )
    assert identify_clue("Grive sp.", ALIASES, 3)[0]["proposed_taxon_id"] == "turdus"
