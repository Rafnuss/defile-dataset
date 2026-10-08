# Défilé de l’Écluse migration counts

Source files and a reproducible build for visible migration counts at Défilé de l’Écluse, France, from 1966 onward.

```bash
uv sync --locked
uv run python scripts/build_dataset.py
uv run python scripts/validate_dataset.py
uv run pytest -q
```

The build reads `raw/historical/count_2021.xlsx`, paired Trektellen exports from 2022 onward, accepted report tables, pinned taxonomy checklists and reviewed configuration. It writes four scientific tables (`count`, `survey`, `taxonomy`, `report_text`) to `output/dataset/`, the interactive audit to `output/audit/report.html`, provenance to `output/metadata.json` and internal processing tables to `interim/`. Required checks must pass before the current output is replaced; blocked builds remain in `output.building/`.

The schema and field definitions live in `config/schema/datapackage.json`. Clock times are stored in UTC; collection dates refer to Europe/Paris. Missing dates do not imply zero birds or no survey. Accepted report prose was extracted and edited with AI assistance; it is not a full transcription. The full 2022 report is unavailable.

GitHub Actions runs tests and builds the audit for pull requests. Successful builds on `main` can publish the audit through GitHub Pages once **Settings → Pages → Source → GitHub Actions** is enabled. Hosted audits use the annual-report URLs in `raw/reports/sources.csv`; local builds link to the local PDF library. Generated products are ignored by Git.
