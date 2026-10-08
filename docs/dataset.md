# Dataset usage

Use count.csv, survey.csv, taxonomy.csv and report_text.csv for analysis. The column dictionary below is generated from the adjacent datapackage.json, copied from config/schema/datapackage.json in the repository. Edit that JSON source to change definitions or validation rules.

To regenerate documentation: `uv run python scripts/generate_dataset_docs.py`. To validate the written CSVs: `uv run python scripts/validate_dataset.py`. A complete build (`uv run python scripts/build_dataset.py`) does both automatically. The validation report is in output/audit/datapackage_validation.json.

Generated CSVs use UTF-8 with a byte-order mark (BOM), so Excel recognizes French accents when opening them directly. In Python, `pandas.read_csv()` reads these files normally; with the standard `csv` module, open them with `encoding="utf-8-sig"`.

## Readable record IDs

The first columns identify records for browsing: survey IDs use `ERA-YYYYMMDD-HHMM`, and count IDs use `ERA-YYYYMMDD-HHMM-SPECIES-normal` (or `reverse`/`local`). Prefixes are B notebook, S spreadsheet, N Naturalist, T Trektellen and C curated. Dates and clocks in IDs are local Europe/Paris; datetime columns remain UTC. Calendar-day closures omit the clock. Counts use their recorded entry clock or historical interval start, never an inherited whole-day survey start; day-level entries without a recorded clock omit it.

SPECIES is the existing eBird code, or the original taxon label normalized to lowercase ASCII with hyphens when no code exists. Collisions receive `-02`, `-03`, etc., in consistent original-source-ID order; supported historical subgroups retain `-partN`. Categories and subgroups from one source entry share the same readable base.

Readable IDs are regenerated on every build. Corrections to dates, clocks or taxa, and changes to collision groups, can change them; they are not persistent publication identifiers. `source_count_id` retains the original observation identity for joins to `interim/processed/observations.csv`; `source_survey_id` retains the original survey identity for joins to source audits and reviewed decisions. Native Trektellen IDs remain in `trektellen_data_id` and `trektellen_count_id`. No ID registry or workbook edits are required.

## Report text and survey coverage

report_text.csv contains only populated curated accounts, with four columns: year, category, key and text. The primary key is (year, category, key). Category is one of species, site, monitoring, weather, results or outreach. For species, key is an existing dataset Avibase ID, including spuh, slash and hybrid accounts. Weather keys are season or an English month name. All allowed category/key combinations are documented and validated below.

Field and analysis methods are combined under monitoring/methods with internal headings; other observations and seasonal events are combined under results/highlights. Content has been reassigned by subject, including staffing/coverage, nocturnal trials and outreach. Accepted prose is maintained in `raw/reports/report_text.csv` and copied into the release. It was extracted and edited with AI assistance; it is not a complete transcription: tables, charts and some other content are omitted. Text remains French with paragraph breaks. Missing rows do not establish species absence; the full 2022 report is unavailable. Shared passages are not independent evidence. The extraction workflow, raw text and processed text are preserved in `archive/report-processing/` and are not build inputs.

`survey.csv` records `survey_coverage` as `complete`, `partial`, `none` or `unknown`, with a short `survey_coverage_comment`. Coverage describes observation inside the stated survey interval, independently of daily coverage or protocol compliance. Complete means systematic counting throughout; partial means only some of the interval was counted; none means no counting; unknown means coverage cannot be established. Count/no-species intervals are assumed complete unless reviewed evidence establishes otherwise. Original HP wording remains in weather and remarks.

Counts are preserved. Positive or presence-only birds contradicting none lead to unknown coverage and an audit finding. Missing dates alone remain unknown. Documented non-counting gaps can create survey rows without zero species counts. Historical decisions are stored directly in the workbook; Trektellen decisions are in `config/survey-status`. The audit retains `survey_status_review.csv` as its established filename. Partial intervals without supported gap times and unknown intervals cannot provide a full-span observed-effort denominator.

Historical empty intervals can be inferred inside declared day windows under the organiser's recording convention, with reviewed exceptions. They create no species zeros or invented measurements. See [survey coverage](survey-coverage.md) for the effort assumptions and [the audit guide](audit.md) for evidence distinguishing empty surveys from missing bird data.

## Scientific use

The tables preserve recorded detail. Only birds are included; unidentified groups remain valid bird concepts. Explicit no-species entries become survey remarks. Source text and processing notes remain separate. Counts retain their original association in `survey_id`, including untimed entries and entries outside the recorded survey interval. These entries carry an explicit date-only `datetime`, so they do not inherit narrower survey timing. The association does not establish interval membership or observed effort. The full internal tables in `interim/processed/` retain original labels, non-birds and excluded overlaps. The audit explains exclusions.

Daily totals are derived from count and survey. Use a count's own timing when supplied and otherwise inherit the linked survey's timing. Clock times are stored in UTC. Convert them to Europe/Paris before choosing the collection day; date-only entries already contain that local day. Group by collection day, taxon and count_category and sum count. Filter count_category=normal for main migration totals. Preserve missing values when all group values are missing. A date alone does not imply midnight. Survey windows do not establish uninterrupted effort or absences; avoid summing nested day/hour windows.

Historical narratives describe the day, without establishing hourly attendance or constant weather. Weather values/codes retain source semantics; several units and possible default zeros still need review. Bird attributes follow the reviewed Trektellen crosswalk. See [bird attributes](bird-attributes.md) and [source processing](processing.md) for the conversion rules and source limitations.

Later overlapping periods are excluded under the interim earliest-start/native-ID rule. Untimed/outside-period entries retain day-level timing; night periods remain as recorded. Independent annual PDF totals do not overwrite observations.

Native IDs support auditing. Historical sheet/row IDs refer to the frozen reference; reordering the workbook requires preserving identities. Source labels that share a checklist concept are documented in [taxonomy](taxonomy.md) and recoverable per entry from the internal observation table.

The output-root metadata.json (`output/metadata.json` by default) records source and generated-file hashes and validation status. This is a local build; publication licence, publisher and release identifiers remain to be agreed. The separate converter (`uv run python scripts/export_gbif.py`) writes Event and Occurrence CSVs for IPT; GBIF publication and interpretation validation remain pending.

Trektellen status is derived reproducibly from structured DEFILE remark tags and `config/survey-status/trektellen-survey-status.csv`. See [survey coverage](survey-coverage.md) for future recording.

## Build and consumers

Run `uv run python scripts/build_dataset.py` after adding paired annual Trektellen exports or changing maintained inputs. The build stages products, checks source conservation and validates all four CSVs before replacing the current output. Failed builds leave previous products available; failure details are in `output.building/audit/`.

See [the pipeline guide](pipeline.md) for input and output locations, and [the column dictionary](table-columns.md) for generated definitions. Historical counts and effort are read only from `raw/historical/count_2021.xlsx`; older workbooks are evidence. Taxonomic decisions remain in `taxonomy/`, and processing settings in `config/`.

The forecast's older two-table reader can use `--dataset interim/processed/`, which contains observations.csv, surveys.csv and a compatibility copy of build metadata. New consumers should use the four released tables. Interpolation, zero-filling and modelling belong in the forecast repository. Run the GBIF converter separately after the build; regenerate the export CSVs after rebuilding to keep them aligned with the research tables.

## Count categories

`count.csv` uses one `count` column and `count_category` (`normal`, `reverse`, `local`). Category rows share `source_count_id`, the original observation ID. Each `count_id` appends its category to the readable source-entry base, after any historical `-partN` subgroup suffix. Normal historical counts can be split by age/sex/plumage; reverse/local quantities are released once per source entry, without inheriting normal-subgroup attributes. Trektellen structured attributes are retained for its category rows.

Explicit zeros are retained. Missing reverse/local source quantities produce no row, which means unknown rather than zero. Presence-only normal records retain a missing count and `count_estimation=x`; that qualifier is not copied to reverse/local quantities. Timing, survey associations and source remarks are retained on each row. The derived daily and audit views still provide separate normal, reverse and local total columns. This replaces the released `count_reverse` and `count_local` columns and changes count IDs (schema v10).
