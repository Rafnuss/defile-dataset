import pandas as pd
import pytest

from defile_dataset.observers import compile_observers, name_key, split_observers


def test_attendance_clocks_and_shared_surname():
    names, review = split_observers(
        "EGf (9h15-17h15); N.Moulin : 9h-19h | Isabelle et Roger Cattin Gasser"
    )
    assert names == ["EGf", "N.Moulin", "Isabelle Cattin-Gasser", "Roger Cattin-Gasser"]
    assert review == []
    assert split_observers("JPM : 9h00 à 17h30 - S. Kimmel en partie : 14h00 à 18h00")[0] == [
        "JPM",
        "S. Kimmel",
    ]


def test_formatting_does_not_merge_different_initials():
    assert name_key("GFELLER E.") == name_key("E. Gfeller")
    assert name_key("Jean-Pierre Matérac") == name_key("Jean Pierre MATERAC")
    assert name_key("M. Maire") != name_key("Dominique Maire")


def test_new_names_and_review_keep_provenance():
    effort = pd.DataFrame(
        [dict(date=pd.Timestamp("2010-09-01"), observers="EGF; M. Maire; trop de monde")]
    )
    counts = pd.DataFrame([dict(id=12, year=2027, observers="Emmanuel GFELLER, Alice Nouveau")])
    publications = pd.DataFrame(
        [
            dict(
                name_original="E. Gfeller",
                source="report",
                source_id="report-2010",
                source_file="report.pdf",
                source_page=2,
                year=2010,
                context="participants",
                extraction="text",
            )
        ]
    )
    aliases = pd.DataFrame(
        [
            dict(alias="EGF", observer_name="Emmanuel Gfeller"),
            dict(alias="E. Gfeller", observer_name="Emmanuel Gfeller"),
        ]
    )
    names, evidence, review = compile_observers(effort, counts, publications, aliases)
    assert set(names.observer_name) == {"Emmanuel Gfeller", "M. Maire", "Alice Nouveau"}
    assert evidence.loc[evidence.source.eq("report"), "source_page"].item() == 2
    assert "unparsed_attendance" in set(review.reason)
    assert "incomplete_identity" in set(review.reason)
    assert "Alice Nouveau" in set(review.fragment)


def test_conflicting_aliases_cannot_silently_merge_people():
    aliases = pd.DataFrame(
        [
            dict(alias="EGF", observer_name="Emmanuel Gfeller"),
            dict(alias="Egf", observer_name="Someone Else"),
        ]
    )
    with pytest.raises(ValueError, match="unique normalized"):
        compile_observers(None, None, None, aliases)


def test_groups_are_reviewed_without_becoming_observers():
    names, review = split_observers("Groupe des Ornithos de Challex; Benjamin Bruno; Baptiste LPO")
    assert names == ["Benjamin Bruno"]
    assert review == ["Groupe des Ornithos de Challex", "Baptiste LPO"]


def test_acknowledgements_formatting_and_incomplete_names():
    from defile_dataset.observers import acknowledgement_names, standard_observer_name

    assert standard_observer_name("GFELLER Emmanuel") == "Emmanuel Gfeller"
    assert standard_observer_name("Jean-Pierre MATÉRAC") == "Jean-Pierre Matérac"
    assert standard_observer_name("John McDonald") == "John McDonald"
    observers = pd.DataFrame(
        [
            dict(
                observer_name="GFELLER Emmanuel",
                identity_status="supplied_name",
                name_variants="GFELLER Emmanuel",
                sources="report",
            ),
            dict(
                observer_name="Emmanuel Gfeller",
                identity_status="mapped_alias",
                name_variants="EGF",
                sources="historical",
            ),
            dict(
                observer_name="M. Maire",
                identity_status="unresolved",
                name_variants="M. Maire",
                sources="report",
            ),
        ]
    )
    thanks, incomplete, duplicates = acknowledgement_names(observers)
    assert thanks.name.tolist() == ["Emmanuel Gfeller", "M. Maire"]
    assert thanks.abbreviated_name.tolist() == ["E. Gfeller", "M. Maire"]
    assert incomplete.empty
    assert duplicates.empty


def test_curated_typos_apply_to_names_and_preserve_source_spelling():
    from pathlib import Path

    from defile_dataset.observers import standard_observer_name

    aliases = pd.read_csv(Path(__file__).parents[1] / "config/observers/name_aliases.csv")
    supplied = [
        "Stephen Hanneberg",
        "Claude Gory",
        "Ronald Moimert",
        "Marie Noëlle Gigon",
        "Sylvie MAS",
        "Ugo DI CAPUA",
        "Anouchka",
    ]
    counts = pd.DataFrame([dict(id=12, year=2025, observers=", ".join(supplied))])
    publications = pd.DataFrame(
        columns=[
            "name_original",
            "source",
            "source_id",
            "source_file",
            "source_page",
            "year",
            "context",
            "extraction",
        ]
    )
    effort = pd.DataFrame(columns=["observers", "date"])
    names, evidence, _ = compile_observers(effort, counts, publications, aliases)
    assert set(names.observer_name) == {
        "Stéphane Henneberg",
        "Claude Géry",
        "Ronald Meinert",
        "Marie-Noëlle Guigon",
        "Sylvie Mas",
        "Ugo Di Capua",
        "Anoushka",
    }
    assert set(evidence.name_original) == set(supplied)
    assert (
        names.loc[names.observer_name.eq("Sylvie Mas"), "identity_status"].item()
        == "supplied_name"
    )
    assert names.loc[names.observer_name.eq("Anoushka"), "identity_status"].item() == "unresolved"
    assert standard_observer_name("M. Maire") == "M. Maire"


def test_adjacent_known_attendees_are_not_a_new_combined_person():
    aliases = pd.DataFrame(
        [
            dict(alias="Stéphane Henneberg", observer_name="Stéphane Henneberg"),
            dict(alias="Lutz Lücker", observer_name="Lutz Lücker"),
        ]
    )
    counts = pd.DataFrame([dict(id=12, year=2025, observers="Stéphane Henneberg Lutz Lücker")])
    publications = pd.DataFrame(
        columns=[
            "name_original",
            "source",
            "source_id",
            "source_file",
            "source_page",
            "year",
            "context",
            "extraction",
        ]
    )
    names, _, _ = compile_observers(
        pd.DataFrame(columns=["observers", "date"]), counts, publications, aliases
    )
    assert set(names.observer_name) == {"Stéphane Henneberg", "Lutz Lücker"}


def test_acknowledgements_preserve_historical_initials():
    from defile_dataset.observers import abbreviated_observer_name

    assert abbreviated_observer_name("R. Nussbaumer") == "R. Nussbaumer"
    assert abbreviated_observer_name("Jean-Pierre Matérac") == "J.-P. Matérac"
    assert abbreviated_observer_name("Raphaël Nussbaumer") == "R. Nussbaumer"


def test_collectives_and_missing_surnames_stay_in_evidence_only():
    decisions = pd.DataFrame(
        [
            dict(name_original="Nos Oiseaux", classification="collective"),
            dict(name_original="CPN Poissy", classification="collective"),
            dict(name_original="Jacques (BE)", classification="incomplete"),
        ]
    )
    publications = pd.DataFrame(
        [
            dict(
                name_original="Jacques (BE)",
                source="report",
                source_id="report-2010",
                source_file="report.pdf",
                source_page=2,
                year=2010,
                context="Jacques (BE)",
                extraction="text",
            )
        ]
    )
    counts = pd.DataFrame(
        [dict(id=12, year=2025, observers="Nos Oiseaux, CPN Poissy, Jean Bisetti")]
    )
    aliases = pd.DataFrame([dict(alias="Jean Bisetti", observer_name="Jean Bisetti")])
    names, evidence, _ = compile_observers(
        pd.DataFrame(columns=["observers", "date"]), counts, publications, aliases, decisions
    )
    assert names.observer_name.tolist() == ["Jean Bisetti"]
    assert {"Nos Oiseaux", "CPN Poissy", "Jacques (BE)"}.issubset(set(evidence.name_original))
