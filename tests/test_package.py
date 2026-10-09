"""The released JSON schema rejects invalid CSVs and drives generated documentation."""
import json
import shutil

import pandas as pd
import pytest

from defile_dataset.package import SCHEMA_FILE, columns, dictionary, validate_package


@pytest.fixture
def package(tmp_path):
    shutil.copyfile(SCHEMA_FILE, tmp_path / "datapackage.json")
    rows = {
        "count": {
            "count_id": "C1-normal",
            "source_count_id": "C1",
            "count_category": "normal",
            "survey_id": "S1",
            "taxon_id": "avibase-451D6FC8",
            "count": "2",
        },
        "survey": {
            "survey_id": "S1",
            "source_survey_id": "S1",
            "datetime": "2026-10-01T06:00:00Z/2026-10-01T07:00:00Z",
            "recording_era": "trektellen",
            "survey_complete": "true",
        },
        "report_text": {},
        "paper_text": {},
        "taxonomy": {"taxon_id": "avibase-451D6FC8", "name": "Red Kite", "source_taxa": "[]"},
    }
    for name, row in rows.items():
        pd.DataFrame(
            [{field: row.get(field, "") for field in columns(name)}] if row else [],
            columns=columns(name),
        ).to_csv(tmp_path / f"{name}.csv", index=False)
    return tmp_path


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("count", "count_category", "invalid"),
        ("count", "source_count_id", ""),
        ("count", "count", "1.5"),
        ("count", "count", "-1"),
        ("count", "count", ""),
        ("count", "count_id", ""),
        ("count", "survey_id", "missing-survey"),
        ("count", "taxon_id", "avibase-00000000"),
        ("count", "datetime", "2026-02-30"),
        ("count", "datetime", "2026-10-01T08:30:00"),
        ("survey", "datetime", "2026-10-01"),
        ("survey", "datetime", "2026-10-01T09:00:00+02:00/2026-10-01T08:00:00+02:00"),
        ("survey", "recording_era", "unknown"),
        ("survey", "survey_complete", "partial"),
        ("survey", "survey_complete", ""),
        ("taxonomy", "source_taxa", "not-json"),
    ],
)
def test_invalid_csv_rejected(package, table, field, value):
    path = package / f"{table}.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, field] = value
    data.to_csv(path, index=False)
    assert not validate_package(package / "datapackage.json")["valid"]


@pytest.mark.parametrize(
    "values, valid",
    [
        (dict(weather_stop="true", survey_comment="Rain all day."), True),
        (dict(weather_stop="true", survey_comment=""), False),
        (dict(weather_stop="true", survey_complete="false", survey_comment="Rain."), False),
        (dict(survey_complete="false", survey_comment=""), False),
        (dict(survey_complete="false", survey_comment="Records lost."), True),
    ],
)
def test_survey_status_rules(package, values, valid):
    path = package / "survey.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    for field, value in values.items():
        data.loc[0, field] = value
    data.to_csv(path, index=False)
    assert validate_package(package / "datapackage.json")["valid"] == valid


def test_duplicate_primary_key_rejected(package):
    path = package / "count.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    pd.concat([data, data], ignore_index=True).to_csv(path, index=False)
    assert not validate_package(package / "datapackage.json")["valid"]


def test_nullable_link_and_presence_rules(package):
    path = package / "count.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, "survey_id"] = ""
    data.to_csv(path, index=False)
    assert not validate_package(package / "datapackage.json")["valid"]
    data.loc[0, "datetime"] = "2026-10-01"
    data.to_csv(path, index=False)
    assert validate_package(package / "datapackage.json")["valid"]
    data.loc[0, "count_estimation"] = "x"
    data.to_csv(path, index=False)
    assert not validate_package(package / "datapackage.json")["valid"]
    data.loc[0, "count"] = ""
    data.to_csv(path, index=False)
    assert validate_package(package / "datapackage.json")["valid"]


def test_json_constraint_change_controls_validation(package):
    path = package / "datapackage.json"
    assert validate_package(path)["valid"]
    descriptor = json.loads(path.read_text())
    count = next(resource for resource in descriptor["resources"] if resource["name"] == "count")
    field = next(field for field in count["schema"]["fields"] if field["name"] == "count")
    field["constraints"]["minimum"] = 3
    path.write_text(json.dumps(descriptor))
    assert not validate_package(path)["valid"]


def test_dictionary_contains_declared_links_and_conditional_rules():
    text = dictionary()
    assert "survey_id` → `survey.survey_id" in text
    assert "An unlinked count must supply its own date" in text
    assert "minimum: 0" in text
    assert "Completeness applies to the interval, not the entire day or season" in text
    assert "A day intersecting any incomplete survey has unknown observed hours" in text
    assert "not enforced by validate_package alone" in text


@pytest.mark.parametrize(
    "category,key,valid",
    [
        ("weather", "july", True),
        ("weather", "effort", False),
        ("species", "avibase-451D6FC8", True),
        ("species", "avibase-00000000", False),
        ("monitoring", "avibase-451D6FC8", False),
    ],
)
def test_report_category_keys_and_taxonomy_link(package, category, key, valid):
    pd.DataFrame([dict(year=2020, category=category, key=key, text="Texte du rapport.")]).to_csv(
        package / "report_text.csv", index=False
    )
    assert validate_package(package / "datapackage.json")["valid"] == valid


def test_accepted_paper_accounts_validate_without_count_taxa(package):
    root = SCHEMA_FILE.parents[2]
    shutil.copyfile(root / "raw/reports/paper_text.csv", package / "paper_text.csv")
    assert validate_package(package / "datapackage.json")["valid"]


@pytest.mark.parametrize("change", ["source_id", "key", "duplicate"])
def test_invalid_paper_identity_rejected(package, change):
    data = pd.DataFrame(
        [
            dict(
                source_id="defile-paper-1996-I",
                category="species",
                key="group-corbeau-freux-choucas-des-tours",
                text="Texte partagé.",
            )
        ]
    )
    if change == "duplicate":
        data = pd.concat([data, data], ignore_index=True)
    else:
        data.loc[0, change] = "unknown"
    data.to_csv(package / "paper_text.csv", index=False)
    assert not validate_package(package / "datapackage.json")["valid"]


@pytest.mark.parametrize(
    "value",
    [
        "2026-10-01",
        "2026-10-01T06:30:00+00:00",
        "2026-10-01T06:30:00Z",
        "2026-10-01T06:30Z",
        "2026-10-01T06:30:00.125Z",
        "2026-10-01T06:00:00Z/2026-10-01T07:00:00Z",
    ],
)
def test_iso_forms_pass_standard_schema_and_project_rules(package, value):
    path = package / "count.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, "datetime"] = value
    data.to_csv(path, index=False)
    assert validate_package(package / "datapackage.json")["valid"]


@pytest.mark.parametrize(
    "value", ["01/10/2026", "2026-13-01", "2026-10-01T24:00:00+02:00", "2026-10-01T08:30:00"]
)
def test_standard_pattern_rejects_bad_iso_syntax(package, value):
    from frictionless import Package

    path = package / "count.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, "datetime"] = value
    data.to_csv(path, index=False)
    report = Package(str(package / "datapackage.json")).validate().to_descriptor()
    assert not report["valid"]
    assert any(
        error["type"] == "constraint-error" for task in report["tasks"] for error in task["errors"]
    )


@pytest.mark.parametrize(
    "table,field,value",
    [
        ("count", "count_estimation", "unknown"),
        ("count", "age", "unreviewed"),
        ("count", "sex", "male"),
        ("count", "plumage", "unreviewed"),
        ("survey", "wind_direction", "XX"),
        ("survey", "precipitation", "unreviewed"),
        ("survey", "wind_speed_bft", "13"),
        ("survey", "wind_speed_bft", "1.5"),
        ("survey", "cloud_cover", "9"),
        ("survey", "cloud_cover", "3.5"),
        ("survey", "visibility", "-1"),
        ("survey", "cloud_height", "-1"),
        ("count", "datetime", "2026-10-01T08:30:00+02:00"),
    ],
)
def test_enums_weather_ranges_and_utc_are_enforced(package, table, field, value):
    path = package / f"{table}.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, field] = value
    data.to_csv(path, index=False)
    assert not validate_package(package / "datapackage.json")["valid"]


def test_valid_weather_bounds_and_provisional_codes_are_preserved(package):
    path = package / "survey.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, ["wind_speed_bft", "cloud_cover", "temperature", "precipitation"]] = [
        "12",
        "8",
        "-15",
        "mist",
    ]
    data.to_csv(path, index=False)
    path = package / "count.csv"
    data = pd.read_csv(path, dtype=str, keep_default_na=False)
    data.loc[0, ["age", "sex", "plumage"]] = ["non_adult", "FC", "W"]
    data.to_csv(path, index=False)
    assert validate_package(package / "datapackage.json")["valid"]


def test_daily_counts_recover_collection_day_from_utc_and_date_only():
    from defile_dataset.consolidate import daily_from_tables, local_dates

    dates = pd.Series(
        [
            "2026-09-30T22:30:00Z",
            "2026-10-01",
            "2026-01-01T23:30:00Z",
            "2026-10-25T00:30:00Z",
            "2026-10-25T01:30:00Z",
        ]
    )
    assert local_dates(dates).tolist() == [
        "2026-10-01",
        "2026-10-01",
        "2026-01-02",
        "2026-10-25",
        "2026-10-25",
    ]
    survey = pd.DataFrame(
        {"survey_id": ["S1"], "datetime": ["2026-09-30T22:30:00Z/2026-10-01T00:30:00Z"]}
    )
    count = pd.DataFrame(
        {
            "count_id": ["C1", "C2", "C3"],
            "survey_id": ["S1", "S1", None],
            "taxon_id": ["avibase-451D6FC8"] * 3,
            "datetime": [None, "2026-09-30T23:00:00Z", "2026-10-01"],
            "count": [3, 2, 1],
            "count_category": ["normal"] * 3,
        }
    )
    daily = daily_from_tables(count, survey)
    assert daily.date.tolist() == ["2026-10-01"] and daily["count"].tolist() == [6]
