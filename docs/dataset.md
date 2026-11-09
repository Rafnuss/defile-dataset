# Défilé de l’Écluse migration dataset

This package contains harmonised bird counts, survey information and a curated taxonomic reference. Start with the tables below; consult [the complete column dictionary](table-columns.md) for complete field descriptions, types, keys, allowed values and validation rules. The adjacent `datapackage.json` contains the same definitions in machine-readable form.

## Files and relationships

| File | One row represents | Main links |
| --- | --- | --- |
| `count.csv` | A recorded quantity or presence for one taxon, movement category and supported subgroup | `survey_id` → `survey.survey_id`; `taxon_id` → `taxonomy.taxon_id` |
| `survey.csv` | A recorded survey interval, including explicitly identified weather stops | `survey_id` identifies the interval |
| `taxonomy.csv` | A harmonised taxon concept | `taxon_id` identifies the concept; `parent_taxon_id` describes the curated identification hierarchy |

Curated annual-report and historical-paper accounts are maintained separately in `output/text/` and are not part of this Zenodo package.

## Essential conventions

- **Rows and birds:** `count` is a numerical quantity; several rows can derive from one source observation. Row counts are not bird numbers.
- **Movements:** select `count_category=normal` for main-direction passage. Reverse-direction and local movements are separate categories and do not identify unique birds.
- **Quantities:** `~` marks an approximate quantity, `>` a lower bound and `x` presence without a numerical count. An empty qualifier does not establish exactness. Empty cells are missing information; zero is an explicit value. Missing records are not automatically zeros.
- **Times:** clock times are UTC. Convert to Europe/Paris before grouping by local collection date; date-only values already denote that local date. Where an observation has no time of its own, use its linked survey's temporal support. A survey link alone does not prove that an observation falls within that interval.
- **Effort:** counting hours exclude weather stops. Historical reconstructed intervals assume continuous counting within documented bounds; weather stops assume zero passage rather than observed absence. Incomplete surveys make daily counting hours unknown. See [survey coverage](survey-coverage.md) before calculating effort.
- **Taxa and traits:** use the curated taxon hierarchy consistently when aggregating. Age, sex and plumage are independent fields; female type does not establish female sex. Read the dictionary before combining classes.
- **Identifiers:** readable count and survey IDs are regenerated and may change after corrections. Source and native IDs support traceability; the readable IDs are not persistent publication identifiers.

CSVs use UTF-8 with a byte-order mark for direct opening in Excel. `pandas.read_csv()` reads them normally; Python's standard `csv` module should use `encoding="utf-8-sig"`.

## Licence and citation

The planned licence for `count.csv`, `survey.csv`, `taxonomy.csv` and accompanying metadata is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), pending confirmation of the rights holder and release credit. The separate third-party text extracts are not included in this package. Source PDFs and software have separate rights.

The publication release, version, DOI and recommended citation remain to be assigned. Cite a frozen release for reproducible analyses rather than an unversioned working copy.

## Further documentation

Read [detailed interpretation and processing notes](dataset-details.md), [source processing](processing.md), [survey coverage](survey-coverage.md), [taxonomy](taxonomy.md) and [bird traits](bird-attributes.md) for decisions beyond the field dictionary. The [audit guide](audit.md) explains review evidence; the [pipeline guide](pipeline.md) describes inputs and rebuilding.

## Maintaining this guide

The package `DATA_GUIDE.md` is generated from `docs/dataset.md`; definitions are maintained in `config/schema/datapackage.json`. Run `uv run python scripts/generate_dataset_docs.py` to refresh the guide, dictionaries and submission notes, or `uv run python scripts/build_dataset.py` for a complete build. Validate existing CSVs with `uv run python scripts/validate_dataset.py`. The build records its revision, hashes and validation results in the separate output metadata and audit files. `output/README.md`, generated from `docs/zenodo.md`, supplies the Zenodo webform text and is excluded from the upload. To validate only the upload files, use `uv run python scripts/validate_dataset.py --dataset output/zenodo`; the default validates all five tables using `output/datapackage.json`.
