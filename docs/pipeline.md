# Build and annual updates

Run from the repository root:

```bash
uv sync --locked
uv run python scripts/build_dataset.py
uv run python scripts/validate_dataset.py  # independently validate an existing build
uv run pytest
```

## Maintained inputs

| Location | Role |
| --- | --- |
| `raw/historical/count_2021.xlsx` | Editable historical count and effort reference; completed import evidence is retained locally in `docs/imports/`. |
| `raw/trektellen/` | Untouched paired annual exports, read from 2022 onward. |
| `raw/reports/` | Accepted report prose, transcribed annual totals and interruption evidence. |
| `taxonomy/source_taxa.csv`, `taxonomy/report_taxa.csv` | Maintained source and report taxon mappings. |
| `taxonomy/reference/` | Pinned external checklists. |
| `config/schema/datapackage.json` | Column definitions, vocabulary, constraints and validation rules. |
| `config/attributes/` | Historical age, sex and plumage mapping rules. |
| `config/survey-status/` | Reviewed Trektellen classification decisions and evidence snapshots. |
| `config/audit-settings/` | Season windows and coverage review notes. |
| `raw/reports/sources.csv` | Annual-report URLs and local PDF paths for audit links. The local reference library is optional. |

## Execution

1. Read historical records, effort and paired Trektellen exports.
2. Resolve taxa, map historical attributes and preserve original source fields.
3. Classify surveys from native tags and reviewed decisions; select eligible counts.
4. Consolidate count, survey and taxonomy; read the accepted report-text CSV directly.
5. Add supported non-counting gaps and historical empty intervals inside declared day windows, splitting reviewed breaks; compute coverage review, exclusions and comparisons.
6. Stage all generated files; validate count conservation, timing, schemas and taxon links.
7. Replace current generated products after required checks pass; refresh dictionaries.

The report extraction and curation workflow is archived. The annual build does not perform OCR, apply editorial corrections or inspect extraction review hashes. Published report totals guide comparison without overwriting recorded counts.

## Generated products

```text
output/
  dataset/                 # count, survey, taxonomy, report_text + schema and README
  audit/                   # findings, exclusions, conservation and validation
  gbif/                    # README and Event/Occurrence CSVs from the separate converter
  metadata.json            # input hashes, output hashes and check results
interim/
  processed/               # complete internal observations and surveys
  derived/                 # daily counts from the released tables
  diagnostics/             # comprehensive mapping and timing results
```

See [the audit guide](audit.md) for evidence files and report interpretation. Complete mappings, including successful cases, are in `interim/diagnostics/`.

Use `--out PATH --interim PATH` to build products in alternate locations. Metadata output hashes are relative to the output root; `interim_sha256` paths are relative to the interim root. A failed build remains in `<output-path>.building/` for inspection and does not replace previous products. The next build clears that staging folder.

`interim/processed/metadata.json` is a compatibility copy for the forecast's older reader. Migrate consumers to `output/dataset/`; see [dataset usage](dataset.md).

## Supporting commands and history

`export_gbif.py` converts the current released tables to `output/gbif/event.csv` and `occurrence.csv` for IPT. Run it after each successful build to refresh the export from the current research tables. The exporter is separate from build validation; publication metadata, persistent exported IDs and GBIF interpretation still need review.

`generate_dataset_docs.py` refreshes schema-derived documentation without rebuilding counts. PDF acquisition and optional review commands remain in the local research checkout; they are not required for the public build. Generated dictionaries are `docs/table-columns.md` and `docs/bird_attribute_codes.csv`.

The local research checkout preserves source snapshots, completed migrations and scientific reviews under `archive/`, `scripts/archive/`, `docs/imports/` and `docs/reviews/`. These are excluded from the public core and are not build inputs. Temporary work belongs in ignored `tmp/`.

When adding or re-exporting a season, use the procedure below. Publication versioning is planned through GitHub, Zenodo and GBIF; the local build does not create a frozen release. `.github/workflows/tests.yml` runs the locked test environment.

The audit report presents one section per validation or source-review check, using the shared result inventory (`audit.json`). Yearly coverage and published-total comparisons are separate sections. See [audit terminology and outputs](audit.md).

## Add or replace a season

Save untouched paired exports as `raw/trektellen/Trektellen_data_2422_YEAR.xlsx` and `Trektellen_headerdata_2422_YEAR.xlsx`. The build discovers paired years from 2022 onward. A missing pair stops the build. Run the commands above; review new taxa, attributes and coverage findings, update maintained mappings where necessary, and rebuild. Mark an unfinished final season provisional when publishing.

Historical corrections belong in `raw/historical/count_2021.xlsx`, with evidence of the change. Completed import scripts are not annual-update commands. Current coverage decisions and future Trektellen tags are described in [survey coverage](survey-coverage.md).

## Continuous integration and hosting

The test workflow runs the locked environment on pushes and pull requests. The audit workflow builds the full dataset on pushes to `main`, pull requests and manual runs, saves audit evidence, and publishes successful `main` reports through GitHub Pages. It uses `--online-report-links` for original PDF URLs; local builds use the reference library. Enable GitHub Actions as the Pages source in repository settings when configuring deployment.

The local pipeline produces current products, not annual archives or frozen releases. See [publication](publication.md) for release preparation and [the script index](../scripts/README.md) for optional commands.
