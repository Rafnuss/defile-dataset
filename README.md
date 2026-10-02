# Défilé de l'Écluse migration counts

Visible-migration counts at Défilé de l'Écluse (Ain/Haute-Savoie, France; 46.1172 N, 5.9149 E),
1966 to today, mostly raptors, storks, herons, pigeons and corvids. This repo holds the raw
files as received, builds two documented tables from them, and reports what needs correcting at
the source.

It is the single source of the count data. Its consumers:

- **defile-migration-forecast** copies `surveys.csv` and `observations.csv` and turns them into
  the model's hourly counts (hour splitting, zero-filling, which flagged rows to drop): those
  choices belong to the model, not here.
- A **GBIF** sampling-event export (planned): `surveys` are the events, `observations` the
  occurrences.

```bash
uv sync
uv run python scripts/build_dataset.py   # -> output/
uv run pytest
```

`output/` (gitignored) gets `surveys.csv`, `observations.csv`, `entry_issues.csv`,
`metadata.json` (build time, commit, a SHA-256 of every input file, check results) and
`report.html`. The build exits non-zero if a check fails. Publish a build as a GitHub release
so consumers can pin a version.

## Principles

- **The raw files are never edited.** `raw/` is the data as received; corrections are code.
- **No row is ever removed.** A correction either changes a value and keeps the original next to
  it (`start_original`, `datetime_original`), or only flags a row (`flags`). What to exclude is
  the user's decision: the forecast drops what its model cannot use, a GBIF export may keep it.
- **Every column is kept**, renamed only where the raw name would be ambiguous.
- **Times are UTC** (`start`, `end`, `datetime`, ...), converted from local time
  (Europe/Paris). `date` is the local calendar date of the survey.

## Raw data

| Path | Content |
| --- | --- |
| `raw/historical/count_2021.xlsx` | All records 1966-2021, cleaned by hand (see below). Sheets `1966-2013` (one total per species per survey, mostly whole days), `2014-2016` (hourly paper forms), `2017-2021` (Naturalist entries, assigned to hours), and `Pression observation` (day survey windows, already merged into the record sheets' `startTimeDay`/`endTimeDay`). |
| `raw/historical/sources/` | The files `count_2021.xlsx` was built from, kept for reference. Not read by the build. |
| `raw/trektellen/` | Yearly Trektellen exports for site 2422, read from 2022 (the 2021 export, day totals only, duplicates the 2021 of `count_2021.xlsx` and is not read): `Trektellen_data_2422_<year>.xlsx` (one row per entry) and `Trektellen_headerdata_2422_<year>.xlsx` (one row per count period). Every year present is read; to add a year, add its two files. |
| `taxonomy/source_taxa.csv` | The only hand-maintained taxonomy file: every historical (French) name and Trektellen species id, mapped to an `avibase_id`, with its `kind` (`bird`, `no_species`, `non_bird`), a `mapping_note` and a `review` mark on judgement calls. |
| `taxonomy/reference/` | The reference checklists, as downloaded: AviList v2025 (extended) and the eBird/Clements v2025 integrated checklist. |

### Manual cleaning of the pre-2021 data

We are using the raw data `data/raw/all_data_défilé_tri_v2023` for all data until 2013 and `data/raw/data_brute_DE_2014_2021` for data between 2014 and 2021. A manual cleaning of this data was necessary as detailed below:

- Split data into (1) 1966-2013 providing daily count, (2) 2014-2016 providing hourly count based on data entered manually and (3) 2017-2021 data from Naturalist providing both list and manual entry.
- Fix startTime and endTime for 2014-2016:
  - 29.09.2014 et 11.10.2014 dans les données brut (data_brute_DE_2014_2021)
  - 09.10.2015, 01.12.2016 et 03.12.2016 dans pressure observation (all_data_défilé_tri_v2023)
- Fix and align startTime and endTime for 2017-2021
  - some sightings were providing without a list and without time. so probably seen during the day, but couldn't assign to a hour slot
  - 2-3 instances of interruption of list during the day: 29.10.2021, 17.11.2021 and 14.09.2017
  - Many case of sightings submitted before startTime or after endTime according to pressure observation. In most case I modified pressure observation, but in some case I deleted time (probably sumbmitted from home?)
  - pressure observation also had about 10 entries which seemed completly wrong, I removed those and use the last/first sightings.
- Delete observations after 19:00 for 2020-9-10 (pressure effort states 19:00 as end time, but there were 3 observations after.)
- Delete the observation of a Marsh Harrier on the 2020-11-03 at 20:05 because this if after endtime
- Delete observations oon the 2021-10-29: time of observations don't make sense.
- Modify time slightly to match end time for 22.Sep.17 19:04 -> 18:59, 14.Sep.19 20:00 -> 19:59, 22.Sep.19 20:00 -> 19:59, 2021-09-02 20:00, 2021-10-20 18:00, 2021-09-01 20:00
- modify time of survey of 2017-11-14 and 2019-07-30
- Delete because of no time provided: Goéland leucophée 29.08.2019, Martinet à ventre blanc 09.09.2019 , Pigeon colombin 12.09.2019, 6 observations on the 17.09.2019, Faucon émerillon 09.10.2020, Grand Cormoran and Pigeon ramier 14.10.2020, Circaète Jean-le-Blanc 17.08.2021, Goéland leucophée 04.09.2021, Aigle royal 11.09.2021, Bec-croisé des sapins 16.09.2021, Aigle royal 21.09.2021, Aigle royal 30.09.2021, Pipit spioncelle 13.10.2021, Faucon pèlerin 14.10.2021, Grive mauvis 25.10.2021, Grive mauvis and Vautour fauve 06.11.2021
- Correct effort on the 6.11.2021 setting all time as it seems like they've just entered all the data at the end of the day 09:00-18:31

These modification and merging of the two dataset was performed manually into `raw/historical/count_2021.xlsx`. That file is the starting point of all processing below: the edits above cannot be re-run, so treat it as raw data.

## Tables

### `surveys.csv`: one row per survey period

A survey is one period of counting with its own start and end: for historical data, one
`(start, end)` of the records (a whole day before 2014, mostly an hour after); for Trektellen,
one count period of the header export (an hour, part of a day or a whole day).

| Column | |
| --- | --- |
| `survey_id` | `H<yyyymmdd>-<hhmm>-<hhmm>` (historical, local times) or `T<Trektellen count id>`. |
| `source` | `historical` or `trektellen`. |
| `date` | Local calendar date. |
| `start`, `end` | Survey period, UTC, after corrections. |
| `start_original`, `end_original` | As recorded. |
| `duplicate_of` | Survey this one overlaps and duplicates (see corrections); empty otherwise. |
| `flags` | Corrections applied, `;`-separated (see below). |
| `day_start`, `day_end`, `sheet` | Historical: that day's whole survey window, and the source sheet. |
| `trektellen_count_id`, `observers`, `observers_active`, `observers_present`, `weather`, `wind_speed_bft`, `wind_speed_ms`, `wind_direction`, `cloud_cover`, `cloud_height`, `precipitation`, `visibility`, `temperature`, `pressure_hpa`, `count_type`, `remarks`, `created`, `created_by`, `changed`, `changed_by` | Trektellen header fields as exported. `0` often means "not recorded" (visibility, temperature, cloud height). |

### `observations.csv`: one row per record

| Column | |
| --- | --- |
| `observation_id` | `H-<sheet>-r<Excel row>` (historical); `T<Trektellen data id>`, or `T<count id>-e<n>` (n-th entry of that count in the export) for exports without data id (2022-2023). |
| `survey_id` | The survey the record belongs to; empty for historical records without time. |
| `source`, `date` | As in `surveys`. |
| `datetime`, `datetime_original` | Trektellen entry time, UTC, after / before correction; empty when not timed, and for all historical records. |
| `taxon_name_original`, `trektellen_species_id` | As recorded. Trektellen names are in the export's language, which varies by year: use the id. |
| `avibase_id`, `taxon_kind` | From `taxonomy/source_taxa.csv`. `taxon_kind`: `bird`, `no_species` (a placeholder some sheets use to record a survey with no bird; no `avibase_id`) or `non_bird` (butterflies, dragonflies; no `avibase_id`). |
| `scientific_name`, `english_name`, `taxon_rank`, `order`, `family`, `taxonomy_source` | From the `avibase_id`: AviList where it has the taxon, field by field, else eBird/Clements (slashes, "sp.", hybrids, eBird groups; English names of AviList subspecies). `taxonomy_source` says which checklist named the taxon. |
| `ebird_code`, `ebird_english_name` | eBird/Clements code and English name of the same `avibase_id`, when eBird has it (defile-migration-forecast uses these names). |
| `count` | Birds. Trektellen: `direction1`, birds moving in the main migration direction. Historical: the recorded total. |
| `flags` | See below. |
| `sheet`, `row`, `time_local`, `in_list`, `estimation`, `detail`, `details`, `comment`, `list_comment`, `remark` | Historical columns as in `count_2021.xlsx` (`time_local`: Naturalist entry time, 2017-2021). |
| `trektellen_data_id`, `trektellen_count_id`, `export_row`, `timestamp_local`, `direction2`, `local`, `remarkable`, `remarkable_local`, `age`, `sex`, `plumage`, `remark`, `height`, `location`, `migration_type`, `count_type`, `exact_direction1`, `exact_direction2`, `sighting_direction`, `group_id` | Trektellen fields as exported. `direction2`: birds in the opposite direction; `local`: non-migrating birds. |

### `entry_issues.csv`

One row per Trektellen count and issue: date, survey, period, issue, a description with the
species and birds concerned, number of entries and birds. The same table opens the report: it
is the feedback to send to the counters.

## Corrections and flags

All corrections are on Trektellen data; the historical data was corrected by hand (above).

| Flag | On | Rule |
| --- | --- | --- |
| `end_clipped_to_dusk`, `start_clipped_to_dawn` | survey | A count period ending more than 45 min after civil dusk (or starting more than 45 min before civil dawn; sun at -6°) is clipped to dusk (dawn). Counts entered the same evening end at most ~30 min after dusk; every one beyond 45 min was entered days to months later, several ending the next morning. |
| `duplicate_survey` (and `duplicate_of` on the survey) | observation | Count periods that overlap count the same birds twice (e.g. a day summary and a detailed list of part of it): the longest of each overlapping group is kept, the others' entries are flagged. |
| `time_adjusted` | observation | Timestamp less than 10 min before its period start, or at or less than 10 min after its end: moved to start + 1 min / end - 1 min. |
| `time_outside_survey` | observation | Timestamp further outside its period. |
| `untimed_in_timed_survey` | observation | No timestamp, in a count where most entries with migrating birds (`count > 0`) have one. |
| `no_survey` | observation | Count id missing from the header export. |
| `no_time` | observation | Historical record without start or end time. |

## Taxonomy

Observations are identified by their **Avibase concept id** (`avibase_id`), stable across
checklists and versions. `taxonomy/source_taxa.csv` maps each source name or id to it, once;
names, ranks and families then come from the reference checklists, never typed by hand:
AviList first, eBird/Clements where AviList has no entry (it lists only species and
subspecies) or leaves a field empty.

Where AviList and eBird draw a species differently, the mapping follows AviList: Hooded Crow
and Carrion Crow are mapped to AviList's subspecies *Corvus corone cornix* and *C. c. corone*
(eBird keeps them as two species). Rows marked `review` in `source_taxa.csv` are the judgement
calls worth a second look.

**Upgrading a checklist:** add the new file to `taxonomy/reference/`, update `AVILIST_FILE` /
`EBIRD_FILE` and the version labels in `src/defile_dataset/taxonomy.py`, rebuild. The check
*Avibase ids in the checklists* lists every id the new versions no longer contain (typically
after a split): re-map those rows. **A new Trektellen species** (an id not in
`source_taxa.csv`) fails the check *Taxa in source_taxa.csv*: add a row for it.

## Checks

Run on every build, listed in the report: unique ids; every observation has its survey;
positive durations; no overlapping surveys (duplicates excluded); surveys in daylight; no survey
over 16 h; timestamps inside their survey; every taxon in `source_taxa.csv`, every bird with an
`avibase_id`, and every `avibase_id` in AviList or eBird; stable observation ids.

## Known limits

- **Days with no record at all are missing** before 2022: effort is only known through
  records. The `Pression observation` sheet has the day windows, including days without
  records; it is not read yet.
- **Observer names** are in `surveys.observers` (Trektellen). The repo is private; publishing
  them needs the observers' agreement.

## Protocol history

Notes from the count organisers, in French. Essential before using the data across years:
coverage, effort and recording resolution all changed.

#### Species considered

- les cibles principales du suivi ont toujours été rapaces/ardéiformes/pigeons/corvidés ; le suivi des passereaux est hétérogène ; historiquement ils n'étaient presque pas noté ; durant la dernière décennie c'est un peu mieux mais le Défilé concentre peu les passereaux contrairement aux cols, et les observateurs ne sont pas toujours présent tôt le matin, donc l'exploitation des données est presque impossible.

#### Data collected

- le dénominateur commun à chaque année depuis 1966 c'est un total/jour/espèce avec l'heure de début et heure de fin du suivi ; pour certaines années nous avons plus de détail (horaire) mais c'est hétérogène.
- les relevés météo n'ont jamais été numérisés, et rien n'était noté avant 2008.
- le nombre d'observateur actif par jour est noté de manière hétérogène depuis 2008 mais pas numérisé, donc la pression d'obs "réelle" n'est pas disponible
- les détails (age, sexe) ont été relevé de manière très hétérogène au fil du temps ; probablement exploitable pour le busard des roseaux depuis les années 2000, mais pour les autres espèces j'en doute

#### Temporal coverage

- Le réel suivi quotidien a débuté en 1993, avant cela le suivi était plus ponctuel, très concentré sur les pigeons en octobre.
- Exception faite de 1983 et 1992, années pendant lesquelles la motivation de quelques observateurs a permis les premiers "vrai suivi".
- En 1993 le Dr Charvoz a commencé à suivre bénévolement tous les jours dès juillet, avec l'aide de J.P. Matérac, M. Maire et d'autres les week-end.
- Jusqu'en 2007 le suivi était assuré uniquement par les bénévoles.
- De 2008 à 2016 le suivi était assuré par un salarié de la LPO la semaine et par des bénévoles les week-end.
- Depuis 2017 le suivi est assurée par 2 salariés de la LPO du lundi au samedi et par des bénévoles les dimanches.

Nous avions saisit les données 1966-2007 du Dr Charvoz en décryptant au mieux ses fiches (écriture de médecin !) mais des infos se sont perdues.
Certains observateurs comme Lutz Lücker ont des souvenirs mémorables de migration des pigeons dont nous n'avons pas trace.

#### Data collection

- de 2008 à 2016 on avait des fiches papiers standard pour noter par heure (heure locale), c'était donc saisie avec des totaux horaires. pour certaines journées il y a seulement un formulaire avec total jour
- de 2017 à 2020 on a de l'ultra-brute car saisie en direct avec Naturalist. donc pas d'heure de début et de fin de suivi dans les données (mais on a ça à coté), seulement l'heure de la saisie de la donnée, donc à quelques minutes près celle du passage des oiseaux "en majorité" car ce mode de saisie était appliqué la semaine par les spotteurs pour les journées assurées par les bénévoles il y a seulement un formulaire avec total jour.
- depuis 2021 on utilise l'appli Trektellen, faite pour le suivi de migration.
