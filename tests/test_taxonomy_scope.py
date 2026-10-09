"""Keep owner-confirmed source species limits when checklists contain broader groups."""
from pathlib import Path

import pandas as pd


def test_owner_confirmed_species_limits():
    root = Path(__file__).resolve().parents[1]
    mappings = pd.read_csv(root / "taxonomy/source_taxa.csv")
    historical = mappings.query("source == 'historical'").set_index("taxon_name_original")
    trektellen = mappings.query("source == 'trektellen'").set_index("trektellen_species_id")
    expected = {
        406: "avibase-59353A05",
        281: "avibase-5983D677",
        410: "avibase-B6C8DDB2",
        173: "avibase-082F3A63",
    }
    for native_id, avibase_id in expected.items():
        assert trektellen.loc[native_id, "avibase_id"] == avibase_id
    for name, avibase_id in {
        "Chardonneret élégant": "avibase-59353A05",
        "Courlis corlieu": "avibase-082F3A63",
        "Cassenoix moucheté": "avibase-D9B001DF",
    }.items():
        assert historical.loc[name, "avibase_id"] == avibase_id
    checklist = pd.read_excel(
        root / "taxonomy/reference/avilist_2025_11jun_extended.xlsx"
    ).set_index("AvibaseID")
    for avibase_id in set(expected.values()) | {"avibase-D9B001DF"}:
        assert checklist.loc[avibase_id, "Taxon_rank"] == "species"
