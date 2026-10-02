# GBIF export: plan

Status: design, not built. Decisions still open are marked **Decide**.

## Reference: Batumi Raptor Count

The closest published dataset: [Batumi Raptor Count (BRC) - Autumn migration
data](https://doi.org/10.15468/ur0vnh) (sampling event, CC0, 2008-2019, published through the
NLBIF IPT). What it does:

| | Batumi | Défilé (proposed) |
| --- | --- | --- |
| Type | Sampling event: Event core, Occurrence and ExtendedMeasurementOrFact extensions | Same |
| Events | 725: one per count day (`BRC_20190812`), date only; protocol and effort as one fixed sentence for the whole dataset | Two levels: the count day, and each survey period as a child event with its own start and end, duration and observers. This is what makes the Défilé data useful (effort per hour), so worth the extra level |
| Occurrences | 460 507: one per record; `individualCount`, `eventTime`, `lifeStage`, `sex`, `locality` (counting station) | Same, from `observations.csv` |
| Ids | Database record id as `occurrenceID` | `observation_id`: Trektellen data id, or sheet and row for 1966-2021. Stable |
| Taxonomy | Scientific name with authority, `vernacularName`, an internal `taxonID` | Scientific name (AviList, else eBird), `taxonID` = Avibase id, `nameAccordingTo` = checklist and version |
| Absences | 18 158 `ABSENT` records with count 0 and a time: entry artefacts, not designed absences | None inferred (below) |
| Observers | `recordedBy` = "BRC", the organisation | Organisation only, unless the observers agree |
| Duplicate counts | Removed between the two stations | Overlapping Trektellen counts flagged; their entries not published |

## Mapping

**Day event** (`eventType` = "Survey day"): `eventID` = `DEFILE-<yyyymmdd>`, `eventDate`, the
site's location fields, `samplingProtocol`.

**Survey event** (one per row of `surveys.csv`): `eventID` = `survey_id`, `parentEventID` = the
day event; `eventDate` as an ISO interval in local time with its offset
(`2025-08-24T06:43+02:00/2025-08-24T21:03+02:00`); `sampleSizeValue` = duration,
`sampleSizeUnit` = "minutes"; `samplingEffort` = number of active observers where recorded;
`eventRemarks` = corrections applied (from `flags`). Location on every event:
`decimalLatitude` / `decimalLongitude` (`site.py`), `coordinateUncertaintyInMeters`,
`countryCode` FR, `locality`.

**Occurrence** (one per row of `observations.csv`): `occurrenceID` = `observation_id`, `eventID`
= `survey_id`, `basisOfRecord` = HumanObservation, `individualCount`, `occurrenceStatus` =
present, `scientificName`, `taxonRank`, `taxonID` = `avibase_id`, `nameAccordingTo`,
`vernacularName`, `eventTime` (Trektellen entry time), `lifeStage` (age), `sex`,
`occurrenceRemarks` (remark, plus corrections applied).

**ExtendedMeasurementOrFact**, per survey event (Trektellen, 2022 on): wind speed and direction,
cloud cover, temperature, visibility, precipitation, observers active and present.

**Not published:** effort markers (`No species`: the event without occurrences says it),
entries of duplicate surveys, non-birds (no Avibase id; possible later via GBIF backbone
names), and observer names.

## Decide

1. **Publisher and route.** Which organisation publishes (LPO, Vogelwarte), through which
   GBIF-endorsed publisher and IPT (GBIF France / PatriNat, or GBIF Switzerland).
2. **Licence.** Batumi uses CC0; CC BY 4.0 is the other GBIF option. Needs the data owners'
   agreement either way.
3. **Directions.** A Trektellen entry has `direction1` (migrating in the main direction),
   `direction2` (opposite direction) and `local` birds. Proposed: one occurrence per non-zero
   part, with `behavior` = "migrating", "migrating, opposite direction" or "local", so a plain
   count of individuals is right without reading a remark. Batumi publishes one count per
   record.
4. **Absences.** The count is complete for raptors, storks, herons, pigeons and corvids, not
   for passerines (README -> Protocol history). Proposed: no inferred absence records, but the
   EML states which taxa are counted completely, so users can infer zeros from the events.
   Explicit absences per day for the target taxa would be ~150 000 extra records.
5. **Observer names.** Organisation only (as Batumi), or names with the observers' consent.
6. **Records with timing problems** (`time_outside_survey`, `untimed_in_timed_survey`): publish
   them, without `eventTime` and with a remark, or leave them out.

## Already checked

- Défilé counts are not on GBIF through another route: within 2 km of the site, GBIF holds ~6 000
  bird records (mostly eBird checklists, ~1 200 opportunistic Faune-France records), against
  ~230 000 count records here.
- Ids are stable (Trektellen data ids since the 2022-2023 re-export), every bird has an Avibase
  id, survey effort is explicit.

## To build

`scripts/export_gbif.py`: `event.txt`, `occurrence.txt`, `extendedmeasurementorfact.txt`,
`meta.xml` and `eml.xml` (metadata from a committed `gbif/metadata.yaml`: title, abstract,
methods from README -> Protocol history, contacts, citation, coverage), zipped as a Darwin Core
Archive. Validate with the [GBIF data validator](https://www.gbif.org/tools/data-validator)
before uploading to the IPT.
