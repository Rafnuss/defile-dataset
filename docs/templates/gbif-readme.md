# GBIF / IPT metadata

Use these entries for IPT metadata. Import `event.csv` as Event core and `occurrence.csv` as its extension; exclude this README from the archive data files.

## Title

Visible bird migration counts at Défilé de l’Écluse, France, since 1966

## Description

Visible bird migration observations from Défilé de l’Écluse, France, since 1966, represented as survey Events and associated bird Occurrences. The linked Zenodo dataset provides the full research tables.

Coverage and methods vary over time. Missing records and empty Events do not establish absence; only main-direction counts belong in migration totals. See the accompanying data paper (in preparation) and, meanwhile, the [GitHub methods and documentation](https://github.com/Rafnuss/defile-dataset).

## Coverage

| Field | Entry |
| --- | --- |
| Dataset type | Sampling-event |
| Geographic coverage | Défilé de l’Écluse, Rhône valley, France (46.117215° N, 5.914877° E). Coordinates represent the monitoring site; historical/alternate locations require review. |
| Temporal coverage | 1966 to the release’s final collection date; identify provisional seasons. Intermittent early coverage, later mainly summer/autumn monitoring. |
| Taxonomic coverage | Birds (Aves), especially raptors and other visible migrants; recording scope varies by period and observer. |
| Keywords | Bird migration; visible migration; raptors; migration counts; Défilé de l’Écluse; France |

## Sampling methods

Visual counts by volunteers and salaried observers, using historical paper records and recent electronic recording. Counts can include estimates; timing retains source resolution. Interval duration is not necessarily active counting effort.

## Quality control

Harmonisation checks quantities, timing, identifiers and taxon links before Darwin Core conversion; see [processing and validation](https://github.com/Rafnuss/defile-dataset/blob/main/docs/processing.md).

## Attribution and publication

| Field | Entry |
| --- | --- |
| Creators / contacts / metadata providers | Complete with agreed names, roles, affiliations and contact details. |
| Publishing organisation | Proposed: Swiss Ornithological Institute (Vogelwarte), Swiss IPT; confirm. |
| License | CC BY 4.0, pending confirmation by the data rights-holders. |
| Version / publication date | Complete for the frozen release. |
| Funding | Complete with confirmed funders and grants, where applicable. |

## Related works and citation

- Data paper, in preparation: *Six decades of visible bird migration counts at Défilé de l’Écluse, France, with documented survey effort*. Add citation and DOI when published.
- Full research dataset: [Zenodo release](https://doi.org/10.5281/zenodo.23598005). Match the exported `references` DOI; add the reciprocal GBIF DOI to Zenodo.
- Code and methods: [GitHub](https://github.com/Rafnuss/defile-dataset). Cite the dataset version used and the published data paper when available.

Import details: [GBIF export guide](https://github.com/Rafnuss/defile-dataset/blob/main/docs/gbif.md). Field structure: [IPT metadata profile](https://ipt.gbif.org/manual/en/ipt/latest/gbif-metadata-profile).
