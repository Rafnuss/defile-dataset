"""Taxonomy: source names -> Avibase concept id -> AviList (eBird where AviList has none).

The observation crosswalk is `taxonomy/source_taxa.csv`: one row per historical (French)
name and per Trektellen species id, giving its `avibase_id` and its `kind` (`bird`,
`no_species`: an effort marker, or `non_bird`: butterflies, dragonflies, ...). Resolved checklist fields
come from the two reference checklists in `taxonomy/reference/`, used as downloaded:

- AviList (species and subspecies, each with its Avibase id): preferred, field by field.
- eBird/Clements: for what AviList has no entry for (slashes, "sp.", hybrids, domestic forms,
  eBird groups) and for fields AviList leaves empty (English names of subspecies), plus the
  eBird code.

`taxonomy/report_taxa.csv` separately maps published report labels to source taxa.

To upgrade either checklist, add the new file to `taxonomy/reference/`, point AVILIST_FILE /
EBIRD_FILE (and the version labels) at it, and rebuild. The "Avibase ids in the checklists"
check then lists every id the new versions no longer contain -- typically a split, where the
old concept is replaced -- and so the rows of source_taxa.csv to re-map.
"""

import os

import pandas as pd

TAXONOMY_DIR = "taxonomy"
SOURCE_TAXA_FILE = os.path.join(TAXONOMY_DIR, "source_taxa.csv")
AVILIST_FILE = os.path.join(TAXONOMY_DIR, "reference", "avilist_2025_11jun_extended.xlsx")
AVILIST_VERSION = "AviList v2025 (11 Jun 2025)"
EBIRD_FILE = os.path.join(
    TAXONOMY_DIR, "reference", "ebird_clements_2025_integrated_checklist.csv"
)
EBIRD_VERSION = "eBird/Clements v2025"

KIND_BIRD = "bird"

# Columns added to every observation, from its avibase_id.
TAXON_COLUMNS = [
    "avibase_id",
    "taxon_kind",
    "scientific_name",
    "english_name",
    "taxon_rank",
    "order",
    "family",
    "taxonomy_source",
    "ebird_code",
]


def read_source_taxa(root: str) -> pd.DataFrame:
    df = pd.read_csv(os.path.join(root, SOURCE_TAXA_FILE))
    return df.astype({"trektellen_species_id": "Int64"})


def read_avilist(root: str) -> pd.DataFrame:
    """AviList species and subspecies, indexed by Avibase id."""
    a = pd.read_excel(os.path.join(root, AVILIST_FILE), sheet_name=0)
    species_name = a[a["Taxon_rank"] == "species"].set_index("Scientific_name")[
        "English_name_AviList"
    ]
    a = a[a["AvibaseID"].notna()].copy()
    # Subspecies have no English name in AviList: "<species name> (<epithet>)".
    binomial = a["Scientific_name"].str.split().str[:2].str.join(" ")
    ssp_name = binomial.map(species_name) + " (" + a["Scientific_name"].str.split().str[2] + ")"
    a["english_name"] = a["English_name_AviList"].fillna(
        ssp_name.where(a["Taxon_rank"] != "species")
    )
    return a.rename(
        columns={
            "Scientific_name": "scientific_name",
            "Taxon_rank": "taxon_rank",
            "Order": "order",
            "Family": "family",
        }
    ).set_index("AvibaseID")[["scientific_name", "english_name", "taxon_rank", "order", "family"]]


def read_ebird(root: str) -> pd.DataFrame:
    """eBird/Clements taxa with an Avibase id, indexed by it."""
    e = pd.read_csv(os.path.join(root, EBIRD_FILE), low_memory=False)
    e = e[e["taxon concept ID"].notna()].copy()
    e["family"] = e["family"].str.replace(r"\s*\(.*\)$", "", regex=True)
    return e.rename(
        columns={
            "scientific name": "scientific_name",
            "English name": "english_name",
            "category": "taxon_rank",
            "species_code": "ebird_code",
        }
    ).set_index("taxon concept ID")[
        ["scientific_name", "english_name", "taxon_rank", "order", "family", "ebird_code"]
    ]


def resolve(avibase_ids: pd.Series, avilist: pd.DataFrame, ebird: pd.DataFrame) -> pd.DataFrame:
    """Taxon fields for each unique Avibase id: AviList first, field by field, then eBird."""
    ids = pd.Index(avibase_ids.dropna().unique(), name="avibase_id")
    a, e = avilist.reindex(ids), ebird.reindex(ids)
    fields = ["scientific_name", "english_name", "taxon_rank", "order", "family"]
    out = a[fields].combine_first(e[fields])[fields]
    out["taxonomy_source"] = (
        pd.Series(AVILIST_VERSION, index=ids)
        .where(a["scientific_name"].notna(), EBIRD_VERSION)
        .where(a["scientific_name"].notna() | e["scientific_name"].notna())
    )
    out["ebird_code"] = e["ebird_code"]
    return out.reset_index()


class Taxonomy:
    """Source taxa + reference checklists, loaded once."""

    def __init__(self, source_taxa: pd.DataFrame, avilist: pd.DataFrame, ebird: pd.DataFrame):
        self.source_taxa, self.avilist, self.ebird = source_taxa, avilist, ebird
        self.taxa = resolve(source_taxa["avibase_id"], avilist, ebird)

    @classmethod
    def load(cls, root: str) -> "Taxonomy":
        return cls(read_source_taxa(root), read_avilist(root), read_ebird(root))

    def _lookup(self, source: str, key: str) -> pd.DataFrame:
        st = self.source_taxa[self.source_taxa["source"] == source]
        st = st[[key, "avibase_id", "kind"]].rename(columns={"kind": "taxon_kind"})
        return st.merge(self.taxa, on="avibase_id", how="left")

    def add_to(self, obs: pd.DataFrame, source: str) -> pd.DataFrame:
        """Add TAXON_COLUMNS to observations of `source` (by French name, or Trektellen id)."""
        key = "taxon_name_original" if source == "historical" else "trektellen_species_id"
        lk = self._lookup(source, key).drop_duplicates(key)
        if source == "historical":
            lk = lk.drop(columns="trektellen_species_id", errors="ignore")
        out = obs.merge(lk, on=key, how="left")
        assert len(out) == len(obs)
        return out
