# Défilé de l’Écluse migration counts

Birds counted on autumn migration at Défilé de l’Écluse (Ain, France), from 1966 to the present. Counters stand at a fixed point and record the birds flying past, by species, from mid-July to December.

This guide explains how to read the three tables. [DATA_DICTIONARY.md](table-columns.md) defines every column and every allowed value; `datapackage.json` holds the same definitions in machine-readable form ([Frictionless Data](https://frictionlessdata.io/)).

## Files

| File | One row is | Links |
| --- | --- | --- |
| `count.csv` | the birds of one taxon counted in one entry, in one direction | `survey_id` → `survey.csv`, `taxon_id` → `taxonomy.csv` |
| `survey.csv` | a survey: a period when someone was counting (or was stopped by the weather) | |
| `taxonomy.csv` | a taxon: a species, subspecies, or a group such as “buzzard sp.” | `parent_taxon_id` → `taxonomy.csv` |

## Reading the counts

- **Direction.** `direction` is `main` for birds migrating in the main direction, `reverse` for birds flying the other way, `local` for birds not passing through. Migration totals use `main` only; never add the three together.
- **Number.** `count` is the number of birds. `count_estimation` says when the observer qualified it: `approximate`, `minimum` (at least this many), or `presence` (birds seen but not counted: `count` is empty). An empty `count_estimation` only means no qualifier was written.
- **Several rows per day.** A day of counting has many rows for the same species (one per entry, and one per age or sex class when recorded). Sum them to get a daily total.
- **Time.** `datetime` is in UTC. It is a time (`2023-09-15T08:12:00Z`) when the entry has one, the survey's interval (`start/end`) when it does not, or a local date (`2023-09-15`) when only the day is known. Convert UTC to Europe/Paris before taking the date.
- **Taxa.** Birds that could not be identified to species are counted under a group (for example “buzzard sp.”). To count every bird of a group, add the rows of its descendants, following `parent_taxon_id`.

## Effort, zeros and missing days

- **Counting time** is the `datetime` intervals of `survey.csv`, excluding rows with `weather_stop = true` (the weather made counting impossible; no bird is assumed to have passed).
- **Complete surveys.** `survey_complete = true` means every bird that passed during the survey is in `count.csv`. When it is `false` (records lost, birds missed), the day's totals are too low by an unknown amount.
- **Zeros.** In a complete survey, a species with no row was not seen: its count is zero, but only from the year it started to be counted systematically (`taxonomy.csv` `systematic_count_start_year`). Before that year, or on a day with no survey, the number is unknown, not zero.
- **Recording changed over time** (`survey.csv` `recording_era`): a daily total per species until 2013 (`notebook`), mostly hourly totals in 2014–2016 (`spreadsheet`), individual entries since 2017 (`naturalist`, then `trektellen` from 2022). Time of day is only available where the record has it.

## Example: daily totals

In Python (pandas):

```python
import pandas as pd

count = pd.read_csv("count.csv")
main = count[count["direction"] == "main"]
start = main["datetime"].str.split("/").str[0]
timed = start.str.contains("T")
date = start.str[:10]  # date-only values are already local
date[timed] = (
    pd.to_datetime(start[timed], utc=True).dt.tz_convert("Europe/Paris").dt.strftime("%Y-%m-%d")
)
daily = main.assign(date=date).groupby(["date", "taxon_id"])["count"].sum(min_count=1)
```

In R, `readr::read_csv()` reads the files directly; with base `read.csv()`, add `fileEncoding = "UTF-8-BOM"`.

## Identifiers

`count_id` and `survey_id` are readable (era letter, local date and time, species code, direction, for example `T-20230915-0812-combuz1-main`) but rebuilt at each release: corrections can change them. To trace a record to the source, use `trektellen_data_id` and `trektellen_count_id` (2022 onward). Cite a versioned release for reproducible work.

## File format

CSV, comma-separated, UTF-8 with a byte-order mark so that Excel shows accented names correctly. Empty cells are missing values. Coded columns use plain English words, listed in DATA_DICTIONARY.md.

## Licence and citation

The planned licence for `count.csv`, `survey.csv`, `taxonomy.csv` and this documentation is [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), pending confirmation by the rights holders. The release version, DOI and recommended citation remain to be assigned.

## More detail

How the records were processed, and the decisions behind them, are documented in the [project repository](https://github.com/Rafnuss/defile-dataset): [interpretation details](dataset-details.md), [survey coverage](survey-coverage.md), [source processing](processing.md), [taxonomy](taxonomy.md) and [bird attributes](bird-attributes.md).
