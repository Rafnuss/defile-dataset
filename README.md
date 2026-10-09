# Défilé de l’Écluse migration counts

Source files and a reproducible build for visible migration counts at Défilé de l’Écluse, France, from 1966 onward.

```bash
uv sync --locked
uv run python scripts/build_dataset.py
uv run python scripts/validate_dataset.py
uv run pytest -q
```

The build reads `raw/historical/count_2021.xlsx`, paired Trektellen exports from 2022 onward, accepted report tables, pinned taxonomy checklists and reviewed configuration. It writes five scientific tables (`count`, `survey`, `taxonomy`, `report_text`, `paper_text`) to `output/dataset/`, the interactive audit to `output/audit/report.html`, provenance to `output/metadata.json` and internal processing tables to `interim/`. Required checks must pass before the current output is replaced; blocked builds remain in `output.building/`.

The schema and field definitions live in `config/schema/datapackage.json`. Clock times are stored in UTC; collection dates refer to Europe/Paris. Missing dates do not imply zero birds or no survey. A survey row says whether its counts hold every bird that passed (`survey_complete`); weather that made counting impossible is a complete count of zero (`weather_stop`). Accepted report prose was extracted and edited with AI assistance; it is not a full transcription. The full 2022 report is unavailable.

GitHub Actions runs the tests and builds the audit after each push to `main`, not before: nothing waits on them, and a failure is fixed afterwards. Successful builds publish the audit through GitHub Pages. Hosted audits use the annual-report URLs in `raw/reports/sources.csv`; local builds link to the local PDF library. Generated products are ignored by Git.

## Documentation

- [Dataset usage](docs/dataset.md) and [generated columns](docs/table-columns.md).
- [Build and annual updates](docs/pipeline.md).
- [Source processing](docs/processing.md) and [survey coverage](docs/survey-coverage.md).
- [Sampling history](docs/sampling-history.md).
- [Taxonomy](docs/taxonomy.md) and [bird attributes](docs/bird-attributes.md).
- [Audit interpretation](docs/audit.md).
- [GBIF export and mapping](docs/gbif.md).
- [Release and publication](docs/publication.md).

Counts are released as separate normal, reverse and local category rows, with readable IDs and original source identities. Filter `count_category=normal` for main migration totals. Readable IDs can change after corrections. The separate converter runs with `uv run python scripts/export_gbif.py` after building; GBIF publication and interpretation validation remain pending.

Research drafts, source-library files and review archives remain local and are not required to build the public dataset. Guides identify these as local evidence rather than linking to absent repository files.
