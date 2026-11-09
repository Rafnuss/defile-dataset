# GBIF export from the canonical CSVs

GBIF provides discovery and an independently interpretable representation of the observations; Zenodo retains the complete canonical research tables, evidence and processing details. The current associated release is [Zenodo 10.5281/zenodo.23598005](https://doi.org/10.5281/zenodo.23598005), configured in `config/gbif.json`. Update this configuration for each research release so the GBIF files refer to the exact tables used to generate them.

## Run the converter

Run after a successful dataset build:

```bash
uv run python scripts/export_gbif.py
```

The converter reads `output/zenodo/count.csv`, `survey.csv`, `taxonomy.csv` and the pinned eBird/Clements checklist. It writes `output/gbif/event.csv`, `occurrence.csv` and a refreshed README. The README supplies concise IPT metadata entries, including a reference to the data paper in preparation and GitHub methods; import only the two CSVs as archive data. Maintain its text in `docs/templates/gbif-readme.md`. CSVs are comma-separated plain UTF-8, with one header row and double-quote text delimiters. Import Events as the IPT Event core and Occurrences as its extension, linked through `eventID`. Map all headers to Darwin Core terms except `references`, which maps to `http://purl.org/dc/terms/references`.

Options:

| Argument | Meaning |
| --- | --- |
| `--input PATH` | Canonical dataset directory; default `output/zenodo`. |
| `--out PATH` | Export directory; default `output/gbif`. |
| `--ebird-checklist PATH` | Checklist with the same source columns as the pinned reference; taxa match by exact Avibase concept ID. Update the checklist version label in `src/defile_dataset/taxonomy.py` when upgrading. |
| `--zenodo-doi DOI` | Override the configured release DOI with a bare DOI or `https://doi.org/` URL. `--zenodo-doi ''` omits references for an unpublished preview. |
| `--coordinate-uncertainty-m METRES` | Reviewed radius of the represented observation area. Default blank: uncertainty has not been established. |

The dataset build replaces `output/gbif/` with its README, so rerun the converter after each build. See the [column comparison](gbif-column-comparison.md) for the Batumi/HawkCount review and the reasons for this field selection.

## Record model and identity

One survey row becomes one Event, including empty intervals, weather stops and incomplete counts. Native intervals are retained, not aggregated into days or split into artificial hours. A count without a time of its own carries its survey interval. Each positive quantity or presence-only (`presence`) row becomes one Occurrence. Main-direction zero quantities remain in Zenodo only, because they do not assert a species absence. Empty Events and weather stops do not create taxon absences.

Main, reverse and local counts remain separate. Only `direction=main` belongs in migration totals. The three quantities must not be summed as a migration total, netted, or treated as a census of unique individual birds. Approximate and lower-bound numbers retain the supplied numerical quantity and its qualification.

Event IDs are `defile:2422:survey:SURVEY_ID`; Occurrence IDs are `defile:2422:count:COUNT_ID`. Remove the corresponding prefix to recover the canonical `survey_id` or `count_id` in the linked Zenodo release. Counts without a survey use `defile:2422:unlinked-day:DATE`, a date-level association with no inferred survey effort. Corrected dates, clocks, taxa or collision groups can change readable canonical IDs; a strategy for persistent exported identities still needs agreement before first GBIF publication.

## Taxonomy: Avibase identity and eBird names

`taxonID` retains the exact canonical Avibase concept ID, such as `avibase-06D9A2C8`. `taxonConceptID` supplies its Avibase link, such as `https://avibase.ca/06D9A2C8`. These are source concept identifiers, not GBIF taxon keys. The exporter joins the pinned eBird/Clements checklist on `taxon concept ID`, never on a similar scientific or English name.

For the identical Avibase concept, eBird supplies `scientificName`, `vernacularName`, source category, order and family. A subspecies without an English label uses the eBird parent species name with the subspecies epithet, for example Hooded Crow (cornix), rather than retaining an outdated English synonym. Other missing checklist fields fall back to the canonical taxonomy fields, retaining the canonical taxonomy-source label when eBird has no scientific name for that concept. `nameAccordingTo` identifies the checklist supplying the scientific name. This is an export mapping; canonical research taxonomy is not rewritten. All 273 taxa in the October 19 build have exact matches in the pinned eBird/Clements v2025 checklist.

Only standard ranks species, subspecies, genus, family, order and class populate `taxonRank`. eBird spuh, slash, hybrid, domestic and group categories remain explained in `taxonRemarks`, with their exact source concept and name retained. No species identification or artificial rank is inferred. Check the interpreted GBIF matching of these groups before publication; the supplied concept remains available even when GBIF assigns a different interpreted classification.

## Exported columns

### Event core

| Field | Source and meaning |
| --- | --- |
| `eventID` | Namespaced canonical survey ID, or generated unlinked-day association. |
| `eventDate` | Native survey date/time interval; fallback Events use the local collection day. UTC timing and interval precision are retained. |
| `samplingProtocol` | Visual counts of migrating birds; blank for unlinked-day fallback Events. No effort amount is inferred. |
| `eventRemarks` | Short public summary: complete, incomplete, weather stop, inferred empty interval or unlinked date. A weather stop means passage was not measured. |
| `dynamicProperties` | JSON `survey_complete`, true `weather_stop`, and `coverage_basis=inferred_empty_interval` where identified from the maintained empty-interval comments. Fallbacks have `event_origin=unlinked_count_date`. |
| `countryCode`, `locality` | Configured site country and name. |
| `locationID` | Stable site label `defile:2422:site`. |
| `decimalLatitude`, `decimalLongitude` | Configured count-point coordinates, 46.117215 and 5.914877. |
| `geodeticDatum` | WGS84. |
| `coordinateUncertaintyInMeters` | Reviewed radius supplied by the optional argument; otherwise blank. |
| `locationRemarks` | Explains that coordinates locate the monitoring site, not each bird; historical/alternate count locations remain to be reviewed. |
| `references` | DOI URL of the corresponding research release from `config/gbif.json` or the command-line override. Omitted for a preview with an empty DOI. |

Complete means the research dataset treats counting as complete within that recorded interval; it does not assert exhaustive taxonomic coverage or justify absences. Inferred historical empty intervals remain marked separately from directly recorded surveys. Detailed `survey_comment` narratives, archive row numbers, observer attendance and correspondence stay in the research tables.

### Occurrence extension

| Field | Source and meaning |
| --- | --- |
| `eventID` | Link to the Event core. |
| `occurrenceID` | Namespaced canonical count ID; one eligible category/subgroup row per Occurrence. |
| `eventDate` | Own count timing, otherwise the survey interval. |
| `basisOfRecord` | HumanObservation. |
| `occurrenceStatus` | Present; zero category quantities are not exported. |
| `individualCount` | Recorded positive quantity for this category; blank for presence-only `presence`. |
| `taxonID`, `taxonConceptID` | Exact source Avibase identifier and its concept URL. |
| `scientificName`, `vernacularName` | Scientific and English names from eBird for the same Avibase ID, with canonical fallback. |
| `taxonRank` | Standard source rank only; no invented species rank for unresolved groups. |
| `nameAccordingTo` | Checklist/version supplying the scientific name. |
| `kingdom`, `phylum`, `class` | Animalia, Chordata, Aves. |
| `order`, `family` | Checklist classification; parenthetical English family descriptions are removed. |
| `taxonRemarks` | Explains nonstandard eBird categories such as slash and spuh. |
| `sex` | Confirmed M → male and F → female. Female-type FC is not translated to female. |
| `lifeStage` | A → adult, J → juvenile. Other codes are not translated. Calendar-year classes and historical I, which includes “> 1 an”, are not assumed equivalent to life stages. |
| `behavior` | Main migration direction, reverse migration direction or local/non-migrating. No compass bearing is inferred. |
| `occurrenceRemarks` | Category interpretation and supplied `approximate`, `minimum` or `presence` qualification. |
| `dynamicProperties` | Released `direction`, supplied `count_estimation` and supplied `age`. Missing values omit keys. |
| Geographic fields | Repeated from the linked Event so independent Occurrence imports retain site context. |
| `references` | Same version-specific research-release DOI as on Events. |

`dynamicProperties` preserves essential source distinctions but does not create searchable GBIF category/age/qualification filters. Standard fields improve interpretation without guaranteeing portal filtering. Check the interpreted records and archive downloads after IPT ingestion, including propagation of geography, unresolved taxa, intervals and category quantities.

## Metadata, Zenodo and publication

Keep full weather, source narratives, processing notes, native IDs, crosswalks, attribute codes, main-direction zero rows and coverage evidence in Zenodo. Keep methods, geographical and temporal scope, contributor attribution, licence and citation instructions in IPT/EML and the Zenodo metadata. Include reciprocal links and describe which exact release generated the GBIF representation. The DOI in the CSVs connects the records to the research release; publication metadata must also carry that relationship.

No `sampleSizeValue`, observer-hours, synthetic Event hierarchy, separate Taxon core or report-text extension is generated. A recorded interval's span is not necessarily active observation time or observer-hours. Report measured effort only where supported.

`report_text.csv` and `paper_text.csv` remain outside the GBIF archive and outside the planned CC BY 4.0 grant unless rights-holder permission is obtained. The planned licence for first-party structured Event/Occurrence data is CC BY 4.0, subject to rights-holder authorization. Confirm publisher, public attribution, persistent IDs and geography; set the machine-readable licence and attribution in IPT/EML. The initial proposal remains the Swiss IPT with Vogelwarte as publisher, subject to agreement. Local generation does not publish or update either GBIF or Zenodo.
