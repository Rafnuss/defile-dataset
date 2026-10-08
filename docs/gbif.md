# GBIF export from the canonical CSVs

GBIF receives a focused representation for discovery and interpretation; GitHub and Zenodo retain the complete canonical research CSVs. One survey row becomes one Event and one count row becomes one Occurrence, with namespaced identifiers derived from the current readable research IDs. Corrections to dates, clocks, taxa or collision groups can change these IDs; persistent exported identities must be settled before first publication. The Batumi comparison is background research; alignment with that dataset is no longer a design objective.

```text
survey.csv → Event core
  survey_id → eventID
  datetime → eventDate (recorded interval)
  coverage and its explanation retained
  samplingProtocol → visual counts of migrating birds

count.csv → Occurrence extension
  count_id → occurrenceID
  survey_id → eventID
  own datetime, or inherited survey interval
  count → individualCount (quantity for this category)
  count category, shared source ID, qualifications and age retained as properties
  confirmed male/female codes → sex

 taxonomy.csv → taxon fields on Occurrences
```

Counts with no linked survey get a clearly identified date-level fallback Event with unknown coverage and no inferred effort. Empty and non-counting survey rows remain Events; they do not generate species absences. Native intervals are not aggregated into days or split into artificial hourly events. Main, reverse and local quantities stay distinct; each count row is exported once.

Run the single converter after the dataset build:

```bash
uv run python scripts/export_gbif.py
```

It reads `output/dataset/count.csv`, `survey.csv` and `taxonomy.csv` and writes the complete `output/gbif/event.csv` and `output/gbif/occurrence.csv`. Upload the first as the IPT Event core and the second as its Occurrence extension, linked through `eventID`. Both are comma-separated UTF-8 with one header row; map headers to the matching Darwin Core terms. IPT handles publication metadata and archive generation. Optional `--input` and `--out` arguments select different dataset/output directories. Rerun the converter after each successful build to keep the GBIF files aligned with the research tables. These GBIF CSVs are plain UTF-8, unlike the BOM-prefixed scientific CSVs.

The column mapping below lists the selected fields. `dynamicProperties` is restricted to information needed to interpret coverage and counts. Detailed weather, source narratives, processing notes, raw observer text, native IDs and taxonomy crosswalks remain in the research CSVs. Standard fields are preferred where meanings are confirmed; life-stage mapping remains pending.

`report_text.csv` is excluded from the GBIF archive. It remains part of the canonical dataset distributed through GitHub and Zenodo; selected methods and citations may inform EML metadata.

The initial publication proposal in the organiser email is to use [the Swiss IPT](https://ipt-swissrd.gbif.ch/) with the Swiss Ornithological Institute (Vogelwarte) as publisher, subject to agreement from the organisers and Vogelwarte.

Publication remains pending: confirm publisher, licence, credit and public attribution; review alternate locations and geographical metadata; document known effort without equating survey span with observed hours; prepare EML with a link to the corresponding Zenodo release; validate GBIF interpretation of timing, zero/presence and reverse/local quantities. Keep the canonical CSVs available through GitHub and Zenodo so all source-resolution information remains available. Versioning belongs to GitHub, Zenodo and GBIF.

## Column mapping

`dynamicProperties.field` means a named key inside a JSON object in the standard Darwin Core `dynamicProperties` column. It is preserved information, not a separately mapped Darwin Core field; dedicated filtering/indexing by GBIF is not promised. Missing values omit the JSON key; numerical zeros remain zero.

## What actually goes into dynamicProperties

There is one `dynamicProperties` column in each GBIF table, containing a JSON object. Only six source fields are eligible for custom keys; the exhaustive mapping below repeats their names to show their origin.

| GBIF table | Allowed custom keys | Why keep them? |
| --- | --- | --- |
| Event | `survey_coverage`, `survey_coverage_comment` | Distinguish full, partial, unknown and non-counting periods; explain the classification. |
| Occurrence | `source_count_id`, `count_category`, `count_estimation`, `age` | Explain the category quantity, its qualification and the counted subgroup. |

Fallback Events also get the generated key `event_origin=unlinked_count_date`, so they cannot be mistaken for recorded surveys. Missing values omit keys, so a particular export may contain fewer keys. Weather, source remarks, processing remarks, raw observer text, native IDs, plumage and crosswalks are not copied into these objects.


## count.csv

| Source column | Current destination | Transformation / limitation | Proposed refinement |
| --- | --- | --- | --- |
| `count_id` | Occurrence.occurrenceID | Prefix defile:2422:count:; one occurrence per released category/subgroup. | Keep. |
| `source_count_id` | Occurrence.dynamicProperties.source_count_id | Shared original observation ID for categories and historical subgroups. | Keep. |
| `count_category` | Occurrence.dynamicProperties.count_category | normal, reverse or local; each has its own individualCount. | Keep categories distinct in analyses. |
| `survey_id` | Occurrence.eventID | Namespaced survey link; missing links get an unlinked-day Event. Original link remains in Zenodo. | Keep. |
| `taxon_id` | Occurrence.taxonID | Joined to taxonomy.taxon_id. | Keep. |
| `datetime` | Occurrence.eventDate | Own timing when supplied; otherwise inherit survey.datetime. Original override remains in Zenodo. | Keep; validate GBIF interpretation of points/intervals/date-only values. |
| `count` | Occurrence.individualCount | Quantity for this count category; zero and missing stay distinct. | Keep; document count_estimation and direction semantics. |
| `count_estimation` | Occurrence.dynamicProperties.count_estimation | Native qualifier; x also sets occurrenceStatus=present without inventing a number. | Keep original code and its documented meaning. |
| `age` | Occurrence.dynamicProperties.age | Native calendar-year/maturity code, not translated to lifeStage. | Add lifeStage only for verified equivalent meanings; retain original age. |
| `sex` | Occurrence.sex, conditionally | M → male; F → female. FC (female type) remains unspecified in GBIF and preserved in Zenodo. | Keep; do not equate female type with female. |
| `plumage` | Not exported; retained in GitHub/Zenodo count.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `remark` | Not exported; retained in GitHub/Zenodo count.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `remark_processing` | Not exported; retained in GitHub/Zenodo count.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `trektellen_data_id` | Not exported; retained in GitHub/Zenodo count.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |

## survey.csv

| Source column | Current destination | Transformation / limitation | Proposed refinement |
| --- | --- | --- | --- |
| `survey_id` | Event.eventID | Prefix defile:2422:survey:; one Event per survey. | Keep. |
| `source_survey_id` | Not exported; retained in GitHub/Zenodo survey.csv | Original internal survey identity for source audits and reviewed decisions. | Keep outside GBIF; settle persistent exported IDs before publication. |
| `datetime` | Event.eventDate | Recorded interval unchanged, including overnight and non-counting intervals. | Keep; interval span is not observed effort. |
| `recording_era` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF; describe relevant methods in metadata. |
| `remark` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `remark_processing` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `trektellen_count_id` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `observers` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Add agreed attribution through metadata/recordedBy after organiser review; retain raw attendance text only in the research dataset. |
| `weather` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `wind_speed_bft` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `wind_direction` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `cloud_cover` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `cloud_height` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `precipitation` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `visibility` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `temperature` | Not exported; retained in GitHub/Zenodo survey.csv | Detailed source information stays in the canonical research dataset. | Keep outside GBIF. |
| `survey_coverage` | Event.dynamicProperties.survey_coverage + eventRemarks | complete/partial/none/unknown; not a species absence indicator. | Keep coverage visible; it is not occurrenceStatus or taxonomic completeness. |
| `survey_coverage_comment` | Event.dynamicProperties.survey_coverage_comment | Explanation of coverage evidence/assumptions. | Keep the coverage explanation; no blanket source-narrative export. |

## taxonomy.csv

| Source column | Current destination | Transformation / limitation | Proposed refinement |
| --- | --- | --- | --- |
| `taxon_id` | Occurrence.taxonID | Joined from count.taxon_id; no separate Taxon core in this archive. | Keep. |
| `scientific_name` | Occurrence.scientificName | Source checklist scientific name. | Keep. |
| `english_name` | Not exported; remains in taxonomy.csv | The converter does not map vernacularName. | Add vernacularName for the English checklist name. |
| `taxon_rank` | Occurrence.taxonRank, conditionally | Only species/subspecies/genus/family/order/class exported; other source categories remain in CSV. | Retain original group category in properties/taxonRemarks as well. |
| `order` | Not exported; remains in taxonomy.csv | The converter does not map the higher taxonomy. | Add Occurrence.order. |
| `family` | Not exported; remains in taxonomy.csv | The converter does not map the higher taxonomy. | Add Occurrence.family. |
| `taxonomy_source` | Occurrence.nameAccordingTo | Checklist/version supplying the scientific name. | Keep. |
| `ebird_code` | Not exported; remains in taxonomy.csv | No mapped field currently. | Keep in the canonical research dataset outside GBIF. |
| `trektellen_species_id` | Not exported; remains in taxonomy.csv | Concept-level list of native IDs; not the ID for a particular occurrence. | Keep in the canonical research dataset outside GBIF. |
| `source_taxa` | Not exported; remains in taxonomy.csv | Concept-level source-label crosswalk, not per-record original identification. | Keep in the canonical research dataset outside GBIF. |

## report_text.csv

Excluded from the GBIF archive. Retained in the canonical dataset on GitHub and Zenodo; selected methods and citations may inform EML metadata.

| Source column | Current destination | Transformation / limitation | Proposed refinement |
| --- | --- | --- | --- |
| `year` | Not exported; remains in report_text.csv | Report year, not necessarily the year of every observation described. | Keep companion table; use selected methods/citations in EML rather than duplicate report prose across Events. |
| `category` | Not exported; remains in report_text.csv | Account subject/category. | Keep companion table; use selected methods/citations in EML rather than duplicate report prose across Events. |
| `key` | Not exported; remains in report_text.csv | Taxon or narrative key; not an Event or Occurrence identifier. | Keep companion table; use selected methods/citations in EML rather than duplicate report prose across Events. |
| `text` | Not exported; remains in report_text.csv | Curated French report prose, not an individual survey/count record. | Keep companion table; use selected methods/citations in EML rather than duplicate report prose across Events. |

## Generated fields and exceptional cases

- `basisOfRecord` is generated as `HumanObservation`.
- `occurrenceStatus` is `present` if the category quantity is positive or the source marks presence-only (`x`); otherwise unspecified. No source zero is mapped to absence.
- Counts without a survey use `defile:2422:unlinked-day:DATE` as their Event link. Its Event date is the local collection day, with unknown coverage and no inferred effort.
- `countryCode` and `locality` are generated from the configured site. Coordinates are not currently exported.
- Current `eventRemarks` exposes survey coverage and timing limitations; `occurrenceRemarks` explains category quantities. Source remark columns stay in Zenodo.
- No `sampleSizeValue`, observer-hours, synthetic daily/hourly hierarchy, separate Taxon core or report-text extension is generated.
