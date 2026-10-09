import pandas as pd

from defile_dataset.reconcile import compare_report_totals


def test_annual_counts_preserve_missing_sources_and_apply_overlap_policy():
    observations = pd.DataFrame(
        {
            "source": ["historical"] * 4,
            "date": pd.to_datetime(["2021-07-18", "2021-07-18", "2021-11-19", "2021-07-19"]),
            "taxon_name_original": ["A", "B", "A", "A"],
            "count": [100, 20, 50, 7],
            "use_for_counts": [True, True, True, False],
        }
    )
    reference = pd.DataFrame(
        {
            "year": [2021] * 4,
            "species": ["A", "A+B", "Unknown", "Absent"],
            "count": [100, 120, 10, 1],
        }
    )
    mappings = pd.DataFrame(
        {
            "species": ["A", "A+B", "Absent"],
            "dataset_source": ["historical"] * 3,
            "dataset_taxa": ["A", "A|B", "C"],
        }
    )
    result = compare_report_totals(observations, reference, mappings).set_index("species")
    assert result.loc["A", "dataset_count"] == 150
    assert result.loc["A+B", "dataset_count"] == 170
    assert result.loc["Absent", "dataset_count"] == 0
    assert pd.isna(result.loc["Unknown", "dataset_count"])
    assert result.loc["A", "report_count"] == 100
    assert set(result.columns) == {"year", "report_count", "dataset_count"}


def test_reference_counts_have_one_value_per_species_year():
    from pathlib import Path

    reference = pd.read_csv(Path(__file__).parents[1] / "raw/reports/annual-totals.csv")
    assert reference.columns.tolist() == ["year", "species", "count"]
    assert not reference.duplicated(["year", "species"]).any()
    assert reference["count"].notna().all()
