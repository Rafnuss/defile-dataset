"""Observer attribution from saved publication extracts and native attendance fields."""

import html
import re
import unicodedata

import pandas as pd


def name_key(name):
    """Compare case, accents, spacing and punctuation; never guess a person's identity."""
    name = re.sub(r"^(.+) ([A-ZÀ-Ý](?:[.\-]?[A-ZÀ-Ý]){0,2}\.)$", r"\2 \1", name)
    text = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in text if c.isalnum() and not unicodedata.combining(c))


def split_observers(text):
    """Remove attendance clocks; retain unrecognised fragments for review."""
    text = html.unescape(text).replace("\\n", ";").replace("\n", ";")
    text = re.sub(r"\([^)]*\)", ";", text)
    text = re.sub(
        r"\b\d{1,2}\s*[hH:]\s*\d{0,2}(?:\s*[-–à]\s*\d{1,2}(?:\s*[hH:]\s*\d{0,2})?)?", ";", text
    )
    text = re.sub(r"\ben partie\b", "", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}\s*[-–]\s*\d{1,2}\b", ";", text)
    # These shared surnames are explicit in the supplied attendance lists.
    text = re.sub(
        r"Isabelle\s+et\s+Roger\s+Cattin[ -]Gasser",
        "Isabelle Cattin-Gasser; Roger Cattin-Gasser",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"Martine\s+et\s+Michel\s+Passaquay",
        "Martine Passaquay; Michel Passaquay",
        text,
        flags=re.I,
    )
    fragments = re.split(r"[,;|+&:/]|\s+(?:et|avec)\s+|\s+[-–]\s+|=>", text)
    names, unresolved = [], []
    for fragment in fragments:
        fragment = re.sub(r"\b(?:de|DE|à|a)\s*$", "", fragment).strip(" -=>")
        fragment = re.sub(r"\s+", " ", fragment)
        if not fragment or not re.search(r"[^\W\d_]", fragment):
            continue
        words = fragment.split()
        person = all(
            re.fullmatch(r"[^\W\d_](?:[^\W\d_]|[.'’\-])*", word, re.UNICODE)
            and (word[0].isupper() or word in {"de", "du", "des", "van", "von", "der", "le", "la"})
            for word in words
        )
        collective = re.search(
            r"\b(?:groupe|école|ecole|formation|classe|famille|club|LPO)\b", fragment, re.I
        )
        if person and len(words) <= 6 and not collective:
            names.append(fragment)
        else:
            unresolved.append(fragment)
    return list(dict.fromkeys(names)), list(dict.fromkeys(unresolved))


def compile_observers(effort, counts, publications, aliases, decisions=None):
    """Return unique supplied identities, source evidence and unresolved extraction text."""
    alias_keys = aliases.alias.map(name_key)
    if alias_keys.duplicated().any():
        raise ValueError("Observer aliases must have unique normalized spellings.")
    canonical = dict(zip(alias_keys, aliases.observer_name))
    # An alias target is final, so successive builds cannot silently create alias chains.
    if any(canonical.get(name_key(value), value) != value for value in canonical.values()):
        raise ValueError("Observer alias targets must be canonical names, not other aliases.")
    canonical.update({name_key(value): value for value in canonical.values()})
    full_aliases = [
        name
        for name in set(aliases.alias) | set(aliases.observer_name)
        if len(name.split()) >= 2
        and "." not in name
        and all(len(word) > 1 for word in name.split())
    ]
    combined_names = re.compile(
        "|".join(re.escape(name) for name in sorted(full_aliases, key=len, reverse=True)), re.I
    )
    evidence = publications.to_dict("records")
    review = []
    for frame, source, source_file, locator in (
        (effort, "historical", "raw/historical/count_2021.xlsx", "effort"),
        (counts, "trektellen", "raw/trektellen", "id"),
    ):
        for index, row in frame.loc[frame.observers.notna()].iterrows():
            text = str(row.observers)
            names, fragments = split_observers(text)
            year = int(row.date.year) if source == "historical" else int(row.year)
            location = (
                f"Pression observation!{index + 2}" if locator == "effort" else f"countid={row.id}"
            )
            path = (
                source_file
                if source == "historical"
                else f"{source_file}/Trektellen_headerdata_2422_{year}.xlsx"
            )
            separated = []
            for name in names:
                matches = combined_names.findall(name)
                if len(matches) >= 2 and not combined_names.sub("", name).strip():
                    separated.extend(matches)
                else:
                    separated.append(name)
            for name in separated:
                evidence.append(
                    dict(
                        name_original=name,
                        source=source,
                        source_id=location,
                        source_file=path,
                        source_page="",
                        year=year,
                        context=text,
                        extraction="observer_field",
                    )
                )
            for fragment in fragments:
                review.append(
                    dict(
                        source=source,
                        source_id=location,
                        year=year,
                        text_original=text,
                        fragment=fragment,
                        reason="unparsed_attendance",
                    )
                )
    evidence = pd.DataFrame(evidence)
    evidence["name_key"] = evidence.name_original.map(name_key)
    evidence["observer_name"] = evidence.name_key.map(canonical)
    # First spelling is deterministic: saved historical evidence precedes current exports.
    spellings = evidence.drop_duplicates("name_key").set_index("name_key").name_original
    evidence["observer_name"] = evidence.observer_name.fillna(evidence.name_key.map(spellings))
    evidence["observer_name"] = evidence.observer_name.map(standard_observer_name)
    evidence["identity_status"] = evidence.observer_name.map(
        lambda name: "unresolved"
        if len(name.split()) == 1
        or re.search(r"(?:^|\s)[A-ZÀ-Ý](?:[-.]?[A-ZÀ-Ý]){0,2}\.?(?:$|\s)", name)
        or re.search(r"(?:^|\s)[A-ZÀ-Ý][A-Za-zÀ-ÿ.-]{0,4}\.(?:$|\s)|[0-9©?]", name)
        else "supplied_name"
    )
    evidence.loc[
        evidence.name_key.isin(canonical) & evidence.identity_status.ne("unresolved"),
        "identity_status",
    ] = "mapped_alias"
    unparsed = evidence.name_original.str.contains(
        r"[0-9©?$&]|\b(?:groupe|école|ecole|formation|classe|famille|club|LPO)\b",
        case=False,
        regex=True,
    )
    evidence.loc[unparsed, "observer_name"] = pd.NA
    evidence.loc[unparsed, "identity_status"] = "unparsed"
    if decisions is not None:
        reviewed = evidence.name_original.map(name_key).map(
            dict(zip(decisions.name_original.map(name_key), decisions.classification))
        )
        excluded = reviewed.isin(["collective", "incomplete"])
        evidence.loc[excluded, "observer_name"] = pd.NA
        evidence.loc[excluded, "identity_status"] = reviewed[excluded]
    evidence = evidence.drop(columns="name_key").drop_duplicates()
    observers = (
        evidence.groupby("observer_name", sort=True)
        .agg(
            name_variants=("name_original", lambda names: " | ".join(sorted(set(names)))),
            sources=("source", lambda names: " | ".join(sorted(set(names)))),
            first_source_year=("year", "min"),
            last_source_year=("year", "max"),
            evidence_rows=("source", "size"),
            identity_status=("identity_status", "first"),
        )
        .reset_index()
    )
    for row in evidence.loc[
        ~evidence.name_original.map(name_key).isin(canonical) | evidence.extraction.eq("ocr")
    ].itertuples():
        review.append(
            dict(
                source=row.source,
                source_id=row.source_id,
                year=row.year,
                text_original=row.context,
                fragment=row.name_original,
                reason="unparsed_name"
                if row.identity_status in {"unparsed", "collective", "incomplete"}
                else "ocr_spelling"
                if row.extraction == "ocr"
                else "incomplete_identity"
                if row.identity_status == "unresolved"
                else "unmapped_name",
            )
        )
    return (
        observers,
        evidence,
        pd.DataFrame(
            review, columns=["source", "source_id", "year", "text_original", "fragment", "reason"]
        ).drop_duplicates(),
    )


def standard_observer_name(name):
    """Use given-name/surname order and regular casing, preserving supplied accents."""
    name = re.sub(r"^(.+) ([A-ZÀ-Ý](?:[.\-]?[A-ZÀ-Ý]){0,2}\.)$", r"\2 \1", name)
    words = name.split()
    first_given = next((i for i, word in enumerate(words) if not word.isupper()), 0)
    if first_given and all(
        word.isupper() and "." not in word and len(word) > 1 for word in words[:first_given]
    ):
        words = words[first_given:] + words[:first_given]
    return " ".join(word.title() if word.isupper() or word.islower() else word for word in words)


def acknowledgement_names(observers):
    """Full supplied names for thanking; keep incomplete names and possible duplicates visible."""
    import difflib

    names = observers.assign(name=observers.observer_name.map(standard_observer_name))
    supplied_initial = names.name.str.fullmatch(
        r"(?:[A-ZÀ-Ý](?:[.\-]?[A-ZÀ-Ý]){0,2}\.?|[A-ZÀ-Ý][a-z]\.) [^\W\d_][^0-9.]*", na=False
    ) & names.name.str.split().str.len().eq(2)
    incomplete = (
        names.identity_status.eq("unresolved") & ~supplied_initial
    ) | names.name.str.contains(r"^(?:Mme|Mr|Mmes|Monsieur|Madame)\b", regex=True)
    pending = names.loc[incomplete, ["observer_name", "name", "sources", "name_variants"]].copy()
    pending["reason"] = "incomplete_name"
    full = (
        names.loc[~incomplete]
        .drop_duplicates("name")
        .sort_values("name", key=lambda s: s.map(name_key))
    )
    full["abbreviated_name"] = full.name.map(abbreviated_observer_name)
    full = full.sort_values(
        "abbreviated_name", key=lambda values: values.str.split(" ", n=1).str[1].map(name_key)
    )
    candidates = []
    records = full.loc[full.identity_status.ne("unresolved")].to_dict("records")
    for i, left in enumerate(records):
        for right in records[i + 1 :]:
            similarity = difflib.SequenceMatcher(
                None, name_key(left["name"]), name_key(right["name"])
            ).ratio()
            if similarity >= 0.88:
                candidates.append(
                    dict(
                        name=left["name"],
                        possible_duplicate=right["name"],
                        similarity=round(similarity, 3),
                    )
                )
    return (
        full[["name", "abbreviated_name", "name_variants", "sources"]].reset_index(drop=True),
        pending.reset_index(drop=True),
        pd.DataFrame(candidates, columns=["name", "possible_duplicate", "similarity"]),
    )


def abbreviated_observer_name(name):
    """Preserve supplied initials or abbreviate the given name; retain the whole surname."""
    given, surname = standard_observer_name(name).split(" ", 1)
    if "." in given:
        initials = given
    else:
        initials = "-".join(part[0].upper() + "." for part in given.split("-"))
    return initials + " " + surname
