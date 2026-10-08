# Source processing and internal records

The build preserves a complete internal ledger in `interim/processed/observations.csv` and `surveys.csv`, then derives the four scientific tables. Historical inputs are the editable `raw/historical/count_2021.xlsx`, including its effort sheet; native Trektellen inputs are paired annual exports from 2022. The separate 2021 export is evidence and is not counted twice. Older workbooks are source evidence, not runtime inputs.

Processing retains original labels, source fields and excluded rows in the internal ledger. Historical preservation begins with the received manually cleaned reference: earlier deletions cannot be reconstructed from the release alone. See manual cleaning (local evidence: `archive/historical-cleaning.md`) and completed imports (local evidence: `docs/imports`). Released columns and constraints are defined by [the schema](../config/schema/datapackage.json); [dataset usage](dataset.md) explains analytical joins and identifiers.

## Tables

### `surveys.csv`: one row per survey period

A survey is one period of counting with its own start and end: for historical data, one `(start, end)` of the records (a whole day before 2014, mostly an hour after); for Trektellen, one count period of the header export (an hour, part of a day or a whole day).

| Column | |
| --- | --- |
| `survey_id` | `H<yyyymmdd>-<hhmm>-<hhmm>` (historical, local times) or `T<Trektellen count id>`. |
| `source` | `historical` or `trektellen`. |
| `date` | Local calendar date. |
| `start`, `end` | Survey period, UTC, after corrections. |
| `start_original`, `end_original` | As recorded. |
| `duplicate_of` | Retained survey overlapped under the interim exclusion policy; empty otherwise. |
| `flags` | Corrections applied, `;`-separated (see below). |
| `day_start`, `day_end`, `sheet` | Historical: that day's whole survey window, and the source sheet. |
| `trektellen_count_id`, `observers`, `observers_active`, `observers_present`, `weather`, `wind_speed_bft`, `wind_speed_ms`, `wind_direction`, `cloud_cover`, `cloud_height`, `precipitation`, `visibility`, `temperature`, `pressure_hpa`, `count_type`, `remarks`, `created`, `created_by`, `changed`, `changed_by` | Trektellen header fields as exported. Some zeros may be unfilled defaults; native zeros are retained until their semantics are established. |

### `observations.csv`: one row per record

| Column | |
| --- | --- |
| `observation_id` | `H-<sheet>-r<Excel row>` (historical); `T<Trektellen data id>`, or `T<count id>-e<n>` (n-th entry of that count in the export) for exports without native data IDs. Current 2022–2023 re-exports contain native IDs. |
| `survey_id` | The survey the record belongs to; empty for historical records without time. |
| `source`, `date` | As in `surveys`. |
| `datetime`, `datetime_original` | Trektellen entry time, UTC, after / before correction; empty when not timed, and for all historical records. Historical entry clocks remain in `time_local`. |
| `taxon_name_original`, `trektellen_species_id` | As recorded. Trektellen names are in the export's language, which varies by year: use the id. |
| `avibase_id`, `taxon_kind` | From `taxonomy/source_taxa.csv`. `taxon_kind`: `bird`, `no_species` (a placeholder some sheets use to record a survey with no bird; no `avibase_id`) or `non_bird` (butterflies, dragonflies; no `avibase_id`). |
| `scientific_name`, `english_name`, `taxon_rank`, `order`, `family`, `taxonomy_source` | From the `avibase_id`: AviList where it has the taxon, field by field, else eBird/Clements (slashes, "sp.", hybrids, eBird groups; English names of AviList subspecies). `taxonomy_source` says which checklist named the taxon. |
| `ebird_code` | eBird/Clements code of the same `avibase_id`, when eBird has it. |
| `count` | Birds. Trektellen: `direction1`, birds moving in the main migration direction. Historical: the recorded total. |
| `flags` | See below. |
| `age`, `sex`, `plumage`, `remark_processing` | Historical attributes mapped per described subgroup in released counts; source ledger rows remain unsplit with only shared whole-row attributes; processing explanations separate from observer text. See the [crosswalk](bird-attributes.md). Native Trektellen attribute values are preserved. |
| `sheet`, `row`, `time_local`, `in_list`, `estimation`, `detail`, `details`, `comment`, `list_comment`, `remark` | Historical columns as in `count_2021.xlsx` (`time_local`: Naturalist entry time, 2017-2021). |
| `trektellen_data_id`, `trektellen_count_id`, `export_row`, `timestamp_local`, `direction2`, `local`, `remarkable`, `remarkable_local`, `age`, `sex`, `plumage`, `remark`, `height`, `location`, `migration_type`, `count_type`, `exact_direction1`, `exact_direction2`, `sighting_direction`, `group_id` | Trektellen fields as exported. `direction2`: birds in the opposite direction; `local`: non-migrating birds. |

## Corrections and flags

Trektellen corrections should be made in the source system and re-exported; historical corrections belong in the reference workbook with documented evidence.

| Flag | On | Rule |
| --- | --- | --- |
| `duplicate_survey` (and `duplicate_of` on the survey) | survey/observation | Interim policy: within each local survey day, retain the earliest-starting period, with the native numeric count ID breaking ties. Exclude later periods overlapping a retained period from processed totals. Compare against retained periods rather than an entire transitive overlap chain; cross-day night spans do not automatically exclude the following day's survey. This rule is for competing native lists, not intentional parent/child sampling events. Retain all original rows and audit findings. This is a working assumption, not proof of duplicate birds. |
| `time_outside_survey` | observation | Any original timestamp strictly outside the native period: preserve it in `datetime_original`, clear processed `datetime` and include the count at day level pending source correction. No boundary nudging. |
| `untimed_in_timed_survey` | observation | Legacy code now annotates every Trektellen entry without a timestamp, including predominantly untimed surveys. Keep at day level; this is a precision limitation, not an exclusion. |
| `no_survey` | observation | Count id missing from the header export. |
| `no_time` | observation | Historical record without start or end time. |
| `no_entries` | survey | A source survey with no observation rows. This flag alone cannot distinguish zero detections, non-counting or missing records; reviewed coverage and the empty-survey audit supply that interpretation. |
| `records_deleted` | survey | 2021-10-29: its records were deleted in the manual cleaning (times made no sense); surveyed, but not "nothing seen". |

### Timing and selection

Keep the full time audit in `entry_issues.csv` and the HTML report. Night periods remain unchanged, eligible and without a processing flag; daylight and long-duration warnings remain in the audit. Former clipping/nudging flags are no longer generated.

`observations.csv` adds `day_id` (`DEFILE-YYYYMMDD`), `time_resolution` (`point`, `interval` or `day`) and `use_for_counts`. The latter excludes only later overlapping native Trektellen periods under the interim rule; it does not remove rows. Historical interval/day support is classified by the received start/end and day-window fields, not independently verified precision. Additional day-only entries contribute once alongside timed entries.

`daily_source_resolution.csv` groups retained entries by day, source and original taxon, with main count, record count, `point_count`, `interval_count`, `day_count`, opposite-direction and local sums. The three resolution components sum to `count`. These describe time support, not observer effort. No species absences or numerical zero counts are filled. Historical empty survey intervals can be added under the declared-window rule in [survey coverage](survey-coverage.md). `reconciliation.csv` records source, retained and excluded main-count sums by category and year; source = retained + all exclusion categories. These are internal reconciliation products, not a final publication selection. `daily_counts.csv` is the simpler daily view derived only from consolidated count + survey, grouped by date/taxon_id, preserving missing reverse/local components. Its numerical sums agree with the retained source components.

Source correction happens in Trektellen, followed by re-export and rebuild. View links use site/date; edit links use the exact native count ID. The category/search filters change only the report display. See [issue #2](https://github.com/Rafnuss/defile-dataset/issues/2).

## Remaining native fields: retain in raw/audit, omit from consolidated tables

| Native field | What was found in 2022–2026 | Decision |
| --- | --- | --- |
| Count `counttype`; header `counttype` | Count entries all empty; headers all `all` | Omit; neither establishes complete protocol or taxonomic coverage. |
| Count `height`, `location`, `exactdirection2`, `sightingdirection` | All empty | Omit until populated and useful. |
| Count `migtype` | 11 populated entries, four distinct codes | Not constant. Keep in raw/audit pending interpretation; add a named field later if useful. |
| Count `exactdirection1` | Two populated entries (`z`, `w`) | Not constant. Keep in raw/audit pending interpretation. |
| Count `submitted`, `remarkable`, `remarkablelocal`, `groupid` | Varying administrative/website fields | Omit from consolidated tables as requested. |
| Header `perc_duration` | Two values, 10 and 30 | Meaning unresolved; retain in raw/audit without deriving effort. |
| Header `hydro`, `hpa` | All empty | Omit for now. |
| Historical `ID liste` | Boolean with limited reuse value | Omit as requested; no invented historical list identifier. |
| Header created/changed/by fields; calendar helper columns | Administrative or derivable | Omit from consolidated tables; retain raw evidence. |

Excluded overlaps are absent from count/survey analytical outputs, but remain fully visible in audit outputs with native IDs, reasons and count impact. Re-export/rebuild after source correction. Unmatched report taxa and report discrepancies do not block this pipeline.

## Weather and observer interpretation

### Historical narratives

The 2014 report PDF p. 8 and 2016 report PDF p. 8 describe hourly weather recording alongside counts: cloud coverage/type, precipitation type/intensity, wind direction/strength and visibility. The 2014 report also says those weather readings were not analysed for lack of time. See the [sampling-history review](sampling-history.md) and stored annual reports. This establishes a recording protocol; it does not supply the original weather readings.

The historical reference and the four archived original workbooks have no structured wind/cloud/precipitation/visibility columns. The original export headers were inspected, including every Alldata workbook tab. What survives is occasional list-comment prose: four distinct weather descriptions in 2014–2016 and seven in the 2017–2021 sheet. These can describe changing conditions, ranges and interruptions, e.g. cloud from 8/8 to 1/8, variable wind, visibility changing during the day, or no monitoring because of rain.

Keep these descriptions in survey.weather, with their times and qualifiers. Do not turn “bise modérée” into a guessed Beaufort number, “bonne visibilité” into metres, or a changing cloud range into a daily average. The released schema accommodates quantitative Trektellen fields alongside historical narratives without implying equivalent measurements. Recover original hourly weather sheets separately if they become available; they would need their own recorded intervals before any comparison or aggregation.

## What active/present observers bring

The field names suggest actively counting people versus all people present. This is an interpretation of the native names and values, not a recovered formal Trektellen definition. The exports do not specify whether a headcount is maximum, typical, mean or a snapshot, nor give its duration. A daily headcount multiplied by day length is therefore not observer-hours.

Named observer logs retain supplied attendance times for attribution without inventing quantitative effort. Dated headcount anomalies are in the metadata inventory (local evidence: `docs/reviews/survey-metadata-2026-10-07/README.md`).

## Reviewed output constraints

The authoritative constraints and code descriptions are in config/schema/datapackage.json. Wind direction uses Dutch compass codes (o=east, z=south, no=northeast, etc.) and var for variable direction. The enum includes the standard sixteen compass points. Precipitation uses the reviewed recorded categories geen (none), regen (rain) and mist (fog, not drizzle); a blank remains unknown. Other future native codes must be reviewed before inclusion in the enum. These are preserved source codes, not translated CSV values.

Wind Beaufort is an integer from 0 to 12, and cloud cover an integer from 0 to 8 eighths. Cloud height and visibility are nonnegative numbers. Visibility in metres is supported by the public English display on 19 September 2026 (8000m); temperature is in Celsius, consistent with the observer notes and Trektellen's published counting guidelines. No arbitrary temperature range is imposed; negative values are valid. Cloud-height units and zero/default semantics still require clarification. Native zeros are retained. General weather narrative remains unrestricted text.

Evidence: saved public count HTML in the review workspace; [19 September count](https://www.trektellen.org/count/view/2422/20260919?language=english) and [Trektellen-hosted counting guidance](https://www.trektellen.org/static/doc/Leeuwen_M_van_Timing_changes_2007_2014.pdf).

Daily narrative transfers are documented in the import evidence (local evidence: `docs/imports/survey-metadata-2026-10-07/README.md`). Narrative attendance does not establish constant hourly headcounts or weather. Dated completeness statistics are retained in the metadata review (local evidence: `docs/reviews/survey-metadata-2026-10-07/README.md`).
