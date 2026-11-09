# GBIF column comparison and recommendations

Reviewed 23 October 2026 against the initial Défilé export, the published Batumi Darwin Core Archive v1.7, and the GBIF-rescued HawkCount archive v1.0. The comparison below records the pre-update baseline. The agreed changes have since been implemented: exact Avibase identity with eBird names, geography, category/qualification remarks, coverage summaries, verified adult/juvenile life stages, and a configurable Zenodo release link. See [the current mapping](gbif.md) for implemented behavior; historical/alternate geography and persistent identities still need publication review.

The present Event/Occurrence structure is useful. The main improvements should be georeferencing, clear interpretation of category quantities, unidentified-taxon handling and links to the corresponding Zenodo release. Copying the entire research schema into GBIF would add little value.

## Evidence and comparison method

The comparison reads each archive's `meta.xml` to identify mapped terms and scans all records to distinguish populated fields from empty template columns. Archive identifiers used to join tables are excluded from mapped-field counts. The assessment concerns the published archives, not an assumption that every field is indexed or filterable in the GBIF portal.

| Dataset | Actual tables and rows | Mapped fields | Interpretation |
| --- | --- | --- | --- |
| Défilé, generated 23 October from the verified 19 October build | 13,787 Events; 235,207 Occurrences | 7 Event; 13 Occurrence | All columns populated somewhere. Additional native properties are nested in JSON. |
| Batumi v1.7, published 2 December 2025 | 725 Events; 460,507 Occurrences; 1,832 ExtendedMeasurementOrFact records | 8 Event; 50 Occurrence; 3 measurement | Every mapped field has at least one nonempty value. Events are calendar days; occurrences retain individual observation times. |
| HawkCount v1.0, rescued archive dated 6 March 2018 | 634,258 Occurrences; no Event core | 217 mapped fields, only 21 populated | A legacy occurrence product, not a useful template for modern count publication: `individualCount`, effort and Event identifiers are empty. This finding does not describe the current HawkCount/NatureCounts database. |

Sources: [Batumi IPT resource](https://ipt.nlbif.nl/resource?r=brc-autumn_migration_counts), [Batumi archive](https://ipt.nlbif.nl/archive.do?r=brc-autumn_migration_counts&v=1.7), [HawkCount GBIF resource](https://www.gbif.org/dataset/8648fdbe-f762-11e1-a439-00145eb45e9a), [rescued HawkCount archive](https://orphans.gbif.org/US/8648fdbe-f762-11e1-a439-00145eb45e9a.zip).

Downloaded archive SHA-256 values:

```text
Batumi:   670ff5a235e59ad8dc9baa0fc6e7ac8573886d44158d662e49e8521816088d1f
HawkCount: 698c4bce18eb4ec10cce445ed7c8f1a60c2e2b6da41bc99150be39c9f44f010f
```

Local inspection evidence is in ignored `tmp/gbif-comparison/`: downloaded archives, `inspect_archives.py`, `archive-summary.json` and `defile-profile.json`.

## Differences in columns

“Missing” below means absent from the published source mapping, rather than blank on some records. Défilé geography currently resides on Events; Batumi geography resides on Occurrences.

| Information | Défilé | Batumi | HawkCount rescued archive | Assessment |
| --- | --- | --- | --- | --- |
| Observation identity | `occurrenceID` | `occurrenceID`, duplicated by `catalogNumber` | `catalogNumber`, `gbifID`; `occurrenceID` empty | Keep our identifier; a duplicate catalogue number is unnecessary. Settle persistence before publication. |
| Survey identity | `eventID` | `eventID`, one daily Event | Empty | Keep native survey Events. Daily aggregation is unnecessary merely to resemble Batumi. |
| Timing | `eventDate`, including UTC points/intervals | `eventDate`, `eventTime`, `year`, `month`, `day`; Event `startDayOfYear`; Occurrence `verbatimEventDate` | Only `year`, `month`, `day` populated | Our timing is more expressive than the daily Event dates. Additional calendar columns are optional redundancy. |
| Count | `individualCount`, explicit `occurrenceStatus` | `individualCount`; no mapped `occurrenceStatus` | Count and status empty | Both Défilé columns are useful. |
| Count direction / local birds | `dynamicProperties.count_category` | `behavior`, with values such as `flying north:  1` | Empty | Retain exact categories; add readable per-record behavior/remarks. A standard term does not automatically become a portal filter. |
| Quantity qualification | `dynamicProperties.count_estimation` | No dedicated mapped qualifier | Empty | Keep the qualifier and explain it in readable remarks where supplied. |
| Sex | `sex` for confirmed male/female | `sex` | Empty | Keep. Unspecified and female-type records must not be guessed. |
| Age | Native `dynamicProperties.age` | `lifeStage` | Empty | Add verified life-stage equivalents while retaining native codes; calendar-year age is not automatically juvenile/adult. |
| Survey coverage and interruptions | Event `eventRemarks`; JSON `survey_complete`, `weather_stop`, `survey_comment` | No corresponding mapped coverage flags | Empty | These are valuable additions in Défilé, but are interpretive context rather than searchable GBIF completeness metrics. |
| Protocol and effort | `samplingProtocol`; no effort amount | `samplingProtocol`, `samplingEffort` | Empty | Batumi's effort is the same seasonal text on every Event, not measured daily hours. Do not copy that as a model of quantified effort. |
| Place | `countryCode`, `locality` | `locationID`, country and locality hierarchy, coordinates, datum, uncertainty and other geographic fields | Country/state/county/locality and verbatim latitude/longitude | Coordinates and a stable site ID are the strongest useful additions. |
| Taxon identity | `taxonID`, `scientificName`, conditional `taxonRank`, `nameAccordingTo` | Those first three plus detailed classification and `taxonRemarks`; no `nameAccordingTo` | Name and some higher classification; taxon ID/rank empty | Keep our checklist provenance. Add higher classification and explanations of unresolved groups. |
| English common name | Missing | `vernacularName` | Empty | Useful, inexpensive addition from `english_name`; secondary priority. |
| Attribution | Planned dataset metadata | `recordedBy`, `identifiedBy`, institutional fields | Institutional codes | Put agreed attribution in EML; use record-level fields only where their role is accurate. |
| Record notes | Same generic `occurrenceRemarks` on every row | Record-specific occurrence/taxon/organism remarks | Empty | Replace repeated instructions with useful row-specific interpretation; place general methods in metadata. |
| Extra measurements | None | ExtendedMeasurementOrFact for health | None | No need to add an extension just to match Batumi. |
| Link to research release | Not yet in CSVs | No mapped occurrence reference field | Empty | Add a link to the exact Zenodo version and describe the relationship in both products' metadata. |

The exact Batumi Event fields are `eventID`, `eventDate`, `startDayOfYear`, `year`, `month`, `day`, `samplingProtocol`, `samplingEffort`.

Its 50 Occurrence fields are `institutionID`, `institutionCode`, `collectionCode`, `basisOfRecord`, `occurrenceID`, `catalogNumber`, `recordedBy`, `individualCount`, `sex`, `lifeStage`, `behavior`, `occurrenceRemarks`, `organismRemarks`, `eventID`, `eventDate`, `eventTime`, `year`, `month`, `day`, `verbatimEventDate`, `locationID`, `continent`, `country`, `countryCode`, `stateProvince`, `municipality`, `locality`, `verbatimLocality`, `locationRemarks`, `decimalLatitude`, `decimalLongitude`, `geodeticDatum`, `coordinateUncertaintyInMeters`, `verbatimCoordinates`, `verbatimCoordinateSystem`, `identifiedBy`, `taxonID`, `scientificName`, `higherClassification`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`, `specificEpithet`, `infraspecificEpithet`, `taxonRank`, `vernacularName`, `taxonRemarks`.

The 21 populated HawkCount fields are `gbifID`, `institutionCode`, `collectionCode`, `basisOfRecord`, `catalogNumber`, `year`, `month`, `day`, `country`, `stateProvince`, `county`, `locality`, `verbatimLatitude`, `verbatimLongitude`, `scientificName`, `kingdom`, `phylum`, `class`, `order`, `family`, `genus`.

## Are our existing fields meaningful?

**Keep the core identifiers, timing, count, status and taxonomy fields.** `basisOfRecord=HumanObservation` and `occurrenceStatus=present` are useful semantic declarations even though constant. `taxonID` supports joining to Zenodo; label it as the supplied taxon identifier, without claiming it is a GBIF taxon key. `nameAccordingTo` preserves the checklist concept independently of GBIF's interpreted taxonomy. `sex` is populated on 5,289 records and remains useful despite sparsity.

**Retain `dynamicProperties` for essential native interpretation, but do not rely on it for discovery.** GBIF's own publishing guidance describes it as not searchable. The exact category and count qualifier still matter to archive users; Zenodo does not make them dispensable when interpreting a GBIF quantity. [GBIF freshwater publishing guide](https://docs.gbif.org/freshwater-data-publishing-guide/en/).

In this export there are 231,817 normal, 37 reverse and 3,353 local Occurrences. Their respective numerical totals are 14,982,738, 559 and 25,097. Summing all categories is not the main-direction migration total, and these observations are not a census of unique individual birds. Keep the original categories; supplement them with `behavior` such as “migration in main count direction”, “migration in reverse count direction” and “local/non-migrating”, and corresponding row-specific `occurrenceRemarks`. Do not infer compass bearings or subtract reverse counts. These wording examples are publication recommendations, not an implemented mapping.

There are 905 approximate counts (`~`) and 967 lower-bound counts (`>`). Their numbers remain useful, but the qualification must accompany them. Prefer readable explanations on these records over repeating the same generic paragraph 235,207 times. Blank qualification means no recorded qualifier, not verified exactness.

**Keep coverage information, but simplify its public presentation.** The Events include 63 weather stops and two incomplete counts. For GBIF, state what was observed, assumed or unavailable. “Counting impossible; no bird assumed to pass” combines a documented observation failure with a biological assumption; recommend “No counting possible because of weather; passage was not measured.” This changes public wording without changing the canonical research policy. Two incomplete Events are documented as missing count data; “some birds passed uncounted” is less precise than explaining the missing records.

The current `survey_comment` also includes archive row references, organiser correspondence, observer names and detailed reasoning. Keep that evidence in Zenodo. Export short public coverage summaries where essential. Inferred historical empty intervals should remain distinguishable from directly documented zero-detection sessions. `survey_complete=true` is not evidence that all species were monitored or that every species absent from the table was absent in the field.

**The current temporal encoding is defensible.** GBIF's interpretation documentation accepts date-times and date-time intervals in `eventDate`, including UTC examples, and explicitly allows publishers to omit redundant calendar fields. Keep UTC precision rather than simplifying observations to dates. Adding `eventTime` can improve archive readability, but GBIF states it is not interpreted; do not assume this adds hour-level portal filtering. [GBIF temporal interpretation](https://techdocs.gbif.org/en/data-processing/temporal-interpretation).

**The exclusion of zero category quantities is appropriate for this representation.** Zero local or reverse birds does not mean the species was absent. GBIF infers absence from a zero count when status is unspecified. Retain zeros in Zenodo, and do not generate species absences from empty Events or weather stops. [GBIF occurrence interpretation issues](https://techdocs.gbif.org/en/data-use/occurrence-issues-and-flags).

## Useful additions, in priority order

1. **Georeference the observation location.** Add `locationID`, `decimalLatitude`, `decimalLongitude`, `geodeticDatum` and an evidence-based `coordinateUncertaintyInMeters`; use `locationRemarks` to explain the observation site and visible passage area. The code contains a configured count point (46.117215, 5.914877), but confirm historical/alternate locations and what area each georeference represents. Do not interpret six decimal places as metre-scale knowledge of bird positions. Darwin Core defines uncertainty as the radius containing the represented location; leave it blank if unknown rather than inventing a radius. [Darwin Core geographic terms](https://dwc.tdwg.org/terms/#coordinateUncertaintyInMeters).
2. **Expose category and qualification meaning in each relevant record.** Keep native JSON values; add `behavior` and meaningful `occurrenceRemarks`. This helps readers and archive users, but does not create guaranteed GBIF category filters. If portal filtering by category is required, validate a publication design for that requirement before release.
3. **Improve taxonomic context.** There are 15,715 exported records with blank `taxonRank`, associated with eBird/Clements group categories such as spuh, slash, hybrid and domestic. Add `kingdom`, `class`, available `order`/`family`, and `taxonRemarks` explaining the original category. Review matching of slash and unidentified groups in GBIF; do not invent a species identification or put “slash” into `taxonRank`.
4. **Connect GBIF to the exact Zenodo release.** Add `dcterms:references` to the definitive source representation, or `associatedReferences` for an associated release/publication, according to the resource relationship. Put the version-specific DOI, release correspondence and citation guidance in EML and the Zenodo record. Preserve a documented ID-to-ID join for that release; a DOI alone cannot recover which research row produced an Occurrence. [Darwin Core reference terms](https://dwc.tdwg.org/terms/#associatedReferences).
5. **Add verified `lifeStage` and `vernacularName`.** Adult `A` and juvenile `J` have direct native labels to review for mapping. Do not automatically translate calendar-year codes `1`–`4`, or `I` (which includes historical “> 1 an”), into juvenile/adult. Retain the exact native code for reproducibility.
6. **Describe effort honestly.** Supply `samplingEffort` or structured effort only where known. An interval's elapsed duration is not automatically active observation time or observer-hours; observer counts cannot be reconstructed from attendance text without further work. Explain missing effort in EML. GBIF recommends effort reporting, with structured Humboldt terms for richer survey datasets, but an extra extension is not needed just to store unsupported values. [GBIF effort recommendations](https://techdocs.gbif.org/en/data-publishing/data-quality-recommendations), [survey monitoring guide](https://docs.gbif.org/guide-publishing-survey-data/en/).

Keep georeferencing on Events and verify that it appears on interpreted Occurrences after IPT ingestion. Repeat fields in the Occurrence mapping if required by the actual publishing path; validate the resulting GBIF record, not only the local CSV headers.

## Division between GBIF and Zenodo

GBIF should remain independently interpretable for discovery and ordinary reuse: what taxon/group, when, where, how many, observation basis, category, essential qualification, and the observation's survey context. Users should not need to download Zenodo simply to learn that a count is local birds or a lower bound.

Zenodo should preserve full canonical tables, explicit zero category rows, original age/sex/plumage codes, source crosswalks, weather, processing notes, coverage evidence, reproducible code and validation outputs. Keep report/paper excerpts subject to their existing separate rights policy. Dataset metadata should provide methods, scope, attribution, licence and citation guidance rather than repeating those paragraphs in every Occurrence.

Do not add institutional placeholders, duplicated catalogue numbers, every calendar component, detailed weather extensions or a synthetic daily/hourly Event hierarchy merely because another archive has them. The useful lesson from Batumi is explicit biological and geographic context, rather than matching its number of columns.
