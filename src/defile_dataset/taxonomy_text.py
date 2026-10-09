"""Review taxonomy clues in source text; no automatic identification changes."""

import re
import unicodedata

from defile_dataset.attributes import split_daily_context

TAXON_CLUE = r"\b(?:mesanges?|merles?|grives?|pipits?|ppt|bruants?|corvides?|alouettes?|berges?|bergeronnettes?|faucons?|falco|accipiter|epervi\w*|autours?|bondrees?|buses?|herons?|aigrettes?|gravelots?|limicoles?|becasseaux?|courlis|colomb\w*|ramiers?|rustiques?|fenetres?|rieuse|melanocephale|sp|hybrides?)\b|homologation refusee|donnee inutilisable"


def normalize_text(text):
    """Use spelling-insensitive keys while preserving original wording in review outputs."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(text.split()).rstrip(" .!")


def taxon_phrase(text):
    """Separate an explicit quantity from a complete identification phrase, without applying it."""
    text = normalize_text(text)
    match = re.match(
        r"^(?P<subset>dont\s+)?(?P<count>\d+)\s*(?:x\s*)?(?P<phrase>[^\d\s].*)$", text
    )
    if match:
        return match["phrase"], int(match["count"]), bool(match["subset"])
    return text, None, False


def identify_clue(text, aliases, source_count):
    """Suggest only exact configured phrases; other taxon mentions need context review."""
    head, _ = split_daily_context(text)
    phrase, quantity, subset = taxon_phrase(head)
    if phrase in aliases:
        if quantity is None:
            scope = "whole_count_candidate"
        elif quantity > source_count:
            scope = "quantity_exceeds_source"
        elif quantity < source_count:
            scope = "subset_requires_split"
        else:
            scope = "whole_count_candidate"
        if subset and quantity == source_count:
            scope = "subset_wording_equals_total_review"
        return aliases[phrase], scope, quantity
    return (
        None,
        "context_review" if re.search(TAXON_CLUE, phrase) else "no_taxonomy_clue",
        quantity,
    )
