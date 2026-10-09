# Accepted entry timing

`reviewed-entry-times.csv` contains accepted source-record decisions from the 9 October 2026 timing cleanup (local evidence: `docs/imports/timing-cleanup-2026-10-09/README.md`). The regular build applies them before count consolidation, retains raw inputs and writes `output/audit/entry_time_corrections.csv`.

Each row uses the stable internal `observation_id` and its local collection `date`. All populated datetime values have UTC offsets; the current file uses UTC.

| Action | Meaning |
| --- | --- |
| `clear` | Remove the processed point clock; leave the released observation datetime empty, preserving the existing survey link as its fallback. |
| `interval` | Replace an unsupported point clock or a missing range with the explicitly supported observation range in `interval_start` / `interval_end`. Broad daily bounds establish support, not individual flock passage times. |
| `point` | Retain or restore the explicit source observation clock in `datetime`. |

An optional `survey_id` corrects a mistaken link to an existing historical hourly survey. It does not create or extend counting effort. Original source survey IDs remain in `survey_id_original`. When a broad observation range spans multiple historical hourly periods, the source association stays available; the observation's own range takes precedence over that association's received timing.

`reason` describes the scientific decision; `evidence` points to the source or dated review. The processor preserves `datetime_original`, `time_local`, native clocks, raw remarks and all quantities/categories. It writes a processing note and flags each change. Later text parsing cannot restore a rejected clock. The configuration is an accepted correction input, not an automatic night/species filter: future exports must be reviewed against their source IDs and evidence.
