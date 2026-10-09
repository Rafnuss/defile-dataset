# Build audit

Open `report.html`: one section for each validation or source-review question. Four groups organise the checks: Surveys, Counts and data integrity, Historical records, and Coverage and published totals. Switch between English and French at the top; original evidence stays in its source language. Click table headings to sort the displayed rows (empty values stay last). Downloads follow their tables. Each section states the result, relevant evidence and a correction location. Passing checks stay concise; large finding tables are expandable with bounded previews. There is no all-entries dump, dashboard or pipeline overview.

| File | Purpose |
| --- | --- |
| `report.html` | Individual check results, correction guidance, daily coverage figures and published-total comparison. |
| `audit.json` | The same check inventory rendered in HTML: status, row count, explanation and evidence file. |
| `validation_findings.csv` | Affected rows from consistency checks, including solar times and night overlap; filter by test. |
| `datapackage_validation.json` | Full released-CSV schema, key and conditional-rule validation. |
| `historical_taxonomy_review.csv` | Owner-reviewed taxonomic mappings, original and released concepts, subgroup quantities, residual-text treatment and unresolved conflicts. |
| `movement_text_review.csv` | Standalone NPP/NNP, loc and H/Halte markers, native and projected main/reverse/local quantities, overrides, already-local records and unresolved conflicts. |
| `count_text_changes.csv` | Residual remark conversions and conflicts, with released IDs, original/remaining text, age and datetime before/after, and processing notes. |
| `count_text_review.csv` | Original clock-like comments, recovered timestamps, remaining text and released source links. |
| `entry_issues.csv` | Source entry/period findings, not every entry within a flagged survey. |
| `overlap_review.csv` | Kept/excluded period pairs, overlap duration and excluded source totals; unresolved retained overlaps block publication. |
| `attribute_quantity_review.csv` | One audit row per detail component, plus an undescribed remainder where the detail total is smaller than the source count. Scientific counts remain unchanged. |
| `attribute_review.csv` | Historical attribute mappings requiring review, separated by outcome in HTML. |
| `survey_status_review.csv` | Classification issues with period start/end and duration, separated by issue in HTML. |
| `interruption_review.csv` | All season coverage findings; HTML shows unresolved dates. |
| `historical_effort_gaps.csv` | Added historical empty intervals (`added`) and reviewed absences cut out of them (`cut`), with released/source IDs, declared day bounds and duration. |
| `empty_survey_review.csv` | Every released survey without bird rows, distinguishing explicit no-species markers, inferred empty intervals, minute boundaries, missing-count data, weather stops and incomplete surveys. |
| `excluded_counts.csv`, `excluded_surveys.csv` | Original excluded records and reasons. |
| `reconciliation.csv` | Source counts equal retained counts plus mutually exclusive exclusion categories. |
| `daily_coverage.csv` | Daily metrics computed only from the final count and survey tables. |
| `coverage/plotly.min.js` | Local Plotly bundle for the interactive coverage heatmap. |
| `report_reconciliation.csv` | Published annual totals alongside current source-derived totals. |

## Interpretation

Validation failures block publication; review warnings may describe legitimate records or unresolved evidence. Tests verify the code separately through pytest.

Sunrise/sunset use solar altitude −0.833° and are calculated to the minute. The night check uses civil twilight (−6°) and retains every positive overlap. The report filter starts at 30 minutes and can be lowered to zero; its threshold is applied to actual overlap duration, replacing the old 45-minute boundary tolerance for this audit. The processing rules for entry timestamps remain unchanged. `night_minutes` is the actual period overlap outside civil twilight. The sunrise/sunset overlap columns include twilight.

All report tables are collapsed initially. Trektellen “View day” links combine every period on the date; “Edit count” identifies the specific source period.

Entry times outside their source period show the largest offset before the start or after the end, in minutes, for each survey. The initial tolerance hides offsets up to 10 minutes; all findings remain in `entry_issues.csv`. This display filter does not change entry timestamps or the processing policy.

The long-survey table retains all periods over 12 hours; its initial filter and build warning threshold are 15 hours. Fifteen hours focuses review while retaining long summer periods as possible legitimate records. Night and duration tables show both metrics: a period can appear in both. Filters affect the view only, not saved evidence, build status or scientific counts. These two tables include all candidate rows, so filtering and sorting operate on the complete set. Other large tables retain bounded previews.

Historical “no attributes assigned” means no age, sex or plumage was mapped. “Some attributes assigned” means at least one field was mapped with unresolved details remaining. Attributes are assigned separately to each described subgroup; an undescribed remainder is normal and has no inferred attributes. Quantity warnings cover only details whose sum exceeds the source count. Full subgroup lineage is in `interim/diagnostics/historical_components.csv`.

The coverage figure uses only final `dataset/count.csv` and `dataset/survey.csv`, after selection, overlap removal and reviewed status integration. Its selector shows entries, surveys, survey hours, numerical bird/reverse/local counts, and status counts. No source totals, excluded records, precision percentages or missing-attribute metrics are mixed into this view.

Entries are final bird rows, including presence-only records. Counts sum recorded numerical values; a missing value is not zero. A date with survey records but no bird rows has zero entries and no numerical bird count. Unlinked bird rows retain their collection day and contribute to entries/counts, with no assumed survey hours.

Surveys count complete intervals intersecting each local calendar day, weather stops excluded. Status metrics count counted, weather-stop and incomplete intervals separately. Survey hours are the union of counted intervals; weather stops are not hours. An incomplete interval makes the day's observed hours unknown. Calendar bounds never contribute hours. Midnight and daylight-saving transitions use Europe/Paris.

The horizontal axis is the actual day of year, restricted to the core season (days 196–335, mid-July through the end of November). Change the display limits in `config/audit-settings/coverage-season.csv`; this does not filter the dataset or CSV. Grey cells have no recorded value; pale blue is an explicit zero. Metrics with a maximum above 100 use log(1 + value) colours to keep small values visible. Hover readouts show the actual date and untransformed value. Figure downloads follow the selected metric/language; `daily_coverage.csv` contains all daily metrics. Plotly supports zooming, daily hover values and exporting the current view. Its JavaScript bundle is stored locally by `defile_dataset.audit_plots` for offline use.

The audit computations are in `defile_dataset.audit` and `defile_dataset.checks`; `defile_dataset.report` only renders their results. Files are staged under `output.building/audit/` before publication. Failed required checks retain the staged report and the previous published products. Source-conservation checks are individual audit results and block publication on failure. Source-reading errors and malformed inputs can still stop before report generation.

Complete internal tables and optional diagnostics are under `interim/`. Build provenance and input/output fingerprints are in `output/metadata.json`.

Published report totals remain independent reference values. The comparison sums retained counts over the calendar year; report seasons and taxon groups may differ. Missing sources and unresolved mappings remain blank. No count is adjusted to force agreement. The dated pilot (local evidence: `docs/reviews/report-pilot-2026-10-07/README.md`) illustrates why matching seasonal scope matters.
