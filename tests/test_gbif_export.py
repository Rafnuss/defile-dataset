"""Check one-to-one survey/count mapping, including unknown quantities and empty events."""

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def export_input(tmp_path):
    (tmp_path / "dataset").mkdir()
    pd.DataFrame(
        [
            [
                "T1-normal",
                "T1",
                "S1",
                "bird",
                "2024-07-31T22:30:00Z",
                5,
                "normal",
                None,
                "I",
                "M",
                None,
            ],
            [
                "T1-reverse",
                "T1",
                "S1",
                "bird",
                "2024-07-31T22:30:00Z",
                2,
                "reverse",
                None,
                "I",
                "M",
                None,
            ],
            [
                "T1-local",
                "T1",
                "S1",
                "bird",
                "2024-07-31T22:30:00Z",
                3,
                "local",
                None,
                "I",
                "M",
                None,
            ],
            ["H1-normal", "H1", "S1", "bird", None, 7, "normal", None, None, None, None],
            ["T2-normal", "T2", None, "bird", "2024-08-02", 4, "normal", None, None, None, None],
            ["T3-normal", "T3", None, "bird", "2024-08-02", None, "normal", "x", None, None, None],
            ["T4-normal", "T4", None, "bird", "2024-08-02", 0, "normal", None, None, None, None],
        ],
        columns=[
            "count_id",
            "source_count_id",
            "survey_id",
            "taxon_id",
            "datetime",
            "count",
            "count_category",
            "count_estimation",
            "age",
            "sex",
            "plumage",
        ],
    ).drop(columns="source_count_id").assign(
        taxon_id="avibase-TEST0001",
        remark="Private source narrative",
        remark_processing="Detailed correction",
    ).to_csv(
        tmp_path / "dataset/count.csv", index=False
    )
    pd.DataFrame(
        [
            ["S1", "2024-07-31T22:00:00Z/2024-08-01T23:00:00Z", "trektellen", "true", None],
            ["S2", "2024-08-01T10:00:00Z/2024-08-01T11:00:00Z", "trektellen", "false", None],
            ["S3", "2024-08-02T22:00:00Z/2024-08-03T22:00:00Z", "curated", "true", "true"],
        ],
        columns=["survey_id", "datetime", "recording_era", "survey_complete", "weather_stop"],
    ).assign(
        survey_comment="Reviewed decision",
        weather="Source weather narrative",
        observers="Observer names",
        temperature=12,
    ).to_csv(
        tmp_path / "dataset/survey.csv", index=False
    )
    pd.DataFrame(
        [
            [
                "avibase-TEST0001",
                "Oldus name",
                "Old name",
                "species",
                "OldOrder",
                "OldFamily",
                "AviList 2025",
            ]
        ],
        columns=[
            "taxon_id",
            "scientific_name",
            "english_name",
            "taxon_rank",
            "order",
            "family",
            "taxonomy_source",
        ],
    ).to_csv(tmp_path / "dataset/taxonomy.csv", index=False)
    pd.DataFrame(
        [
            [
                "avibase-TEST0001",
                "Milvus milvus",
                "Red Kite",
                "species",
                "Accipitriformes",
                "Accipitridae (Hawks, Eagles, and Kites)",
            ]
        ],
        columns=[
            "taxon concept ID",
            "scientific name",
            "English name",
            "category",
            "order",
            "family",
        ],
    ).to_csv(tmp_path / "ebird.csv", index=False)
    return tmp_path


def test_export_preserves_survey_and_count_rows(export_input):
    script = Path(__file__).parents[1] / "scripts/export_gbif.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--input",
            str(export_input / "dataset"),
            "--out",
            str(export_input / "gbif"),
            "--ebird-checklist",
            str(export_input / "ebird.csv"),
            "--zenodo-doi",
            "10.5281/zenodo.1234567",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    events = pd.read_csv(export_input / "gbif/event.csv").set_index("eventID")
    occurrences = pd.read_csv(export_input / "gbif/occurrence.csv").set_index("occurrenceID")
    assert len(events) == 4 and len(occurrences) == 6  # T4 is a zero
    assert occurrences.individualCount.sum() == 21
    assert occurrences.loc["defile:2422:count:T1-normal", "eventID"] == "defile:2422:survey:S1"
    assert occurrences.loc["defile:2422:count:T1-normal", "eventDate"] == "2024-07-31T22:30:00Z"
    assert (
        occurrences.loc["defile:2422:count:H1-normal", "eventDate"]
        == events.loc["defile:2422:survey:S1", "eventDate"]
    )
    assert (
        events.loc["defile:2422:survey:S1", "eventDate"]
        == "2024-07-31T22:00:00Z/2024-08-01T23:00:00Z"
    )
    properties = json.loads(occurrences.loc["defile:2422:count:T1-normal", "dynamicProperties"])
    assert properties["count_category"] == "normal"
    assert (
        properties["age"] == "I"
        and occurrences.loc["defile:2422:count:T1-normal", "sex"] == "male"
    )
    assert set(properties) == {"count_category", "age"}
    assert (
        "Private source narrative" not in occurrences.to_csv()
        and "Detailed correction" not in occurrences.to_csv()
    )
    assert occurrences.loc["defile:2422:count:T2-normal", "eventDate"] == "2024-08-02"
    assert (
        occurrences.loc["defile:2422:count:T2-normal", "eventID"]
        == "defile:2422:unlinked-day:2024-08-02"
    )
    assert "sampleSizeValue" not in events.columns
    assert json.loads(events.loc["defile:2422:survey:S2", "dynamicProperties"]) == {
        "survey_complete": False,
    }
    assert (
        json.loads(events.loc["defile:2422:survey:S3", "dynamicProperties"])["weather_stop"]
        is True
    )
    assert "Incomplete" in events.loc["defile:2422:survey:S2", "eventRemarks"]
    assert "Weather stop" in events.loc["defile:2422:survey:S3", "eventRemarks"]
    assert (
        "Observer names" not in events.to_csv()
        and "Source weather narrative" not in events.to_csv()
        and "Reviewed decision" not in events.to_csv()
    )
    assert pd.isna(events.loc["defile:2422:unlinked-day:2024-08-02", "samplingProtocol"])
    assert not occurrences.eventID.isin(["defile:2422:survey:S2", "defile:2422:survey:S3"]).any()
    assert pd.isna(occurrences.loc["defile:2422:count:T3-normal", "individualCount"])
    assert occurrences.loc["defile:2422:count:T3-normal", "occurrenceStatus"] == "present"
    # A zero quantity would read as an absence in GBIF: it is not exported.
    assert "defile:2422:count:T4-normal" not in occurrences.index
    assert occurrences.occurrenceStatus.eq("present").all()
    assert occurrences.eventID.isin(events.index).all()
    assert occurrences.taxonID.eq("avibase-TEST0001").all()
    assert occurrences.taxonConceptID.eq("https://avibase.ca/TEST0001").all()
    assert occurrences.scientificName.eq("Milvus milvus").all()
    assert occurrences.vernacularName.eq("Red Kite").all()
    assert occurrences.nameAccordingTo.eq("eBird/Clements v2025").all()
    assert occurrences["family"].eq("Accipitridae").all()
    assert occurrences["order"].eq("Accipitriformes").all()
    assert occurrences["class"].eq("Aves").all()
    assert occurrences.lifeStage.isna().all()  # I includes historical >1 year, not a life stage.
    assert "reverse" in occurrences.loc["defile:2422:count:T1-reverse", "behavior"]
    assert (
        "not part of migration totals"
        in occurrences.loc["defile:2422:count:T1-local", "occurrenceRemarks"]
    )
    assert (
        "Presence without" in occurrences.loc["defile:2422:count:T3-normal", "occurrenceRemarks"]
    )
    assert events["references"].eq("https://doi.org/10.5281/zenodo.1234567").all()
    assert occurrences["references"].eq("https://doi.org/10.5281/zenodo.1234567").all()
    assert events.decimalLatitude.notna().all() and occurrences.decimalLongitude.notna().all()
    assert events.coordinateUncertaintyInMeters.isna().all()
    assert occurrences.locationID.eq("defile:2422:site").all()
    assert "passage was not measured" in events.loc["defile:2422:survey:S3", "eventRemarks"]
    assert (
        occurrences.loc[
            occurrences.dynamicProperties.map(
                lambda value: json.loads(value)["count_category"]
            ).eq("reverse"),
            "individualCount",
        ].sum()
        == 2
    )
    assert (
        occurrences.loc[
            occurrences.dynamicProperties.map(
                lambda value: json.loads(value)["count_category"]
            ).eq("local"),
            "individualCount",
        ].sum()
        == 3
    )
    assert set(path.name for path in (export_input / "gbif").iterdir()) == {
        "event.csv",
        "occurrence.csv",
        "README.md",
    }


def test_export_group_qualifiers_and_coverage(export_input):
    checklist = pd.read_csv(export_input / "ebird.csv")
    checklist.loc[0, ["scientific name", "English name", "category"]] = [
        "Milvus milvus/migrans",
        "Red/Black Kite",
        "slash",
    ]
    checklist.to_csv(export_input / "ebird.csv", index=False)
    counts = pd.read_csv(export_input / "dataset/count.csv")
    counts.loc[0, ["age", "count_estimation"]] = ["A", "~"]
    counts.loc[1, ["age", "count_estimation"]] = ["J", ">"]
    counts.loc[2, ["age", "sex"]] = ["1", "FC"]
    counts.to_csv(export_input / "dataset/count.csv", index=False)
    surveys = pd.read_csv(export_input / "dataset/survey.csv")
    surveys.loc[0, "survey_comment"] = "Empty interval inferred from private source evidence."
    surveys.to_csv(export_input / "dataset/survey.csv", index=False)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts/export_gbif.py"),
            "--input",
            str(export_input / "dataset"),
            "--out",
            str(export_input / "gbif"),
            "--ebird-checklist",
            str(export_input / "ebird.csv"),
            "--zenodo-doi",
            "",
            "--coordinate-uncertainty-m",
            "2500",
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    events = pd.read_csv(export_input / "gbif/event.csv").set_index("eventID")
    occurrences = pd.read_csv(export_input / "gbif/occurrence.csv").set_index("occurrenceID")
    assert "references" not in occurrences and "references" not in events
    assert "Zenodo reference omitted" in result.stdout
    assert occurrences.scientificName.eq("Milvus milvus/migrans").all()
    assert occurrences.taxonRank.isna().all()
    assert occurrences.taxonRemarks.str.contains("category: slash").all()
    assert occurrences.loc["defile:2422:count:T1-normal", "lifeStage"] == "adult"
    assert occurrences.loc["defile:2422:count:T1-reverse", "lifeStage"] == "juvenile"
    assert pd.isna(occurrences.loc["defile:2422:count:T1-local", "lifeStage"])
    assert pd.isna(occurrences.loc["defile:2422:count:T1-local", "sex"])
    assert "Approximate" in occurrences.loc["defile:2422:count:T1-normal", "occurrenceRemarks"]
    assert "lower bound" in occurrences.loc["defile:2422:count:T1-reverse", "occurrenceRemarks"]
    assert occurrences.coordinateUncertaintyInMeters.eq(2500).all()
    assert events.coordinateUncertaintyInMeters.eq(2500).all()
    assert (
        json.loads(events.loc["defile:2422:survey:S1", "dynamicProperties"])["coverage_basis"]
        == "inferred_empty_interval"
    )
    assert "private source evidence" not in events.to_csv()


def test_export_keeps_source_taxonomy_when_avibase_concept_is_not_in_ebird(export_input):
    checklist = pd.read_csv(export_input / "ebird.csv")
    checklist.loc[0, ["taxon concept ID", "scientific name"]] = ["avibase-OTHER001", "Oldus name"]
    checklist.to_csv(export_input / "ebird.csv", index=False)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts/export_gbif.py"),
            "--input",
            str(export_input / "dataset"),
            "--out",
            str(export_input / "gbif"),
            "--ebird-checklist",
            str(export_input / "ebird.csv"),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    occurrences = pd.read_csv(export_input / "gbif/occurrence.csv")
    assert occurrences.taxonID.eq("avibase-TEST0001").all()
    assert occurrences.scientificName.eq("Oldus name").all()
    assert occurrences.vernacularName.eq("Old name").all()
    assert occurrences.nameAccordingTo.eq("AviList 2025").all()


def test_export_subspecies_english_name_uses_ebird_parent(export_input):
    checklist = pd.read_csv(export_input / "ebird.csv")
    checklist.loc[0, ["scientific name", "English name", "category"]] = [
        "Corvus cornix cornix",
        None,
        "subspecies",
    ]
    checklist.loc[1] = [
        "avibase-PARENT01",
        "Corvus cornix",
        "Hooded Crow",
        "species",
        "Passeriformes",
        "Corvidae",
    ]
    checklist.to_csv(export_input / "ebird.csv", index=False)
    result = subprocess.run(
        [
            sys.executable,
            str(Path(__file__).parents[1] / "scripts/export_gbif.py"),
            "--input",
            str(export_input / "dataset"),
            "--out",
            str(export_input / "gbif"),
            "--ebird-checklist",
            str(export_input / "ebird.csv"),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    occurrences = pd.read_csv(export_input / "gbif/occurrence.csv")
    assert occurrences.taxonID.eq("avibase-TEST0001").all()
    assert occurrences.scientificName.eq("Corvus cornix cornix").all()
    assert occurrences.vernacularName.eq("Hooded Crow (cornix)").all()
    assert occurrences.taxonRank.eq("subspecies").all()
