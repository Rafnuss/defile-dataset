# Commands

Run from the repository root with `uv run python scripts/<name>.py`.

| Script | Purpose |
| --- | --- |
| `build_dataset.py` | Build and validate scientific tables, audit and provenance. |
| `validate_dataset.py` | Validate existing tables; `--report PATH` optionally saves results. |
| `export_gbif.py` | Convert the current tables to Event and Occurrence CSVs for IPT. |
| `generate_dataset_docs.py` | Refresh schema-derived documentation and the dataset README. |

See [the pipeline guide](../docs/pipeline.md) for execution order and locations. Historical import scripts and exploratory diagnostics remain in the local research checkout and are not annual-update commands.
