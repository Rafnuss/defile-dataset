# Survey coverage and observed effort

The build discovers paired annual data/header exports in `raw/trektellen`. Add the next year's files and run `uv run python scripts/build_dataset.py`.

## Definition

A survey row is a period when someone was responsible for the count. Three columns describe it:

| Column | Values | Meaning |
| --- | --- | --- |
| `survey_complete` | `true` / `false` | `true`: every bird that passed during the interval is in `count.csv`. The normal case. `false`: someone was counting but birds are known to have passed uncounted (records lost or deleted, birds noted as missed). Rare. |
| `weather_stop` | `true` / blank | `true`: weather (rain, fog, storm) made counting impossible over the whole interval. Always with `survey_complete = true`: no bird is assumed to pass, so its zeros are assumed, not observed. |
| `survey_comment` | text | A short note on the decision: why the interval is a weather stop or incomplete, what was cut out of it, or an assumption made. Not the observers' narrative, which stays in `remark` and `weather`. |

Times nobody was counting are not survey rows: an absence (lunch, leaving early, arriving late) is cut out of the survey, and a day not monitored for a reason other than weather has no row. A missing date therefore says nothing; it is not a zero.

Every survey is complete unless a decision says otherwise. A weather stop with known times is its own row, so the hours counted and the hours assumed stay apart; when the times are unknown, the survey stays one complete row and the comment says when it rained. A whole day rained out is one row with calendar-day bounds when no hours were recorded. Weather stops are kept as rows so a user can test the assumption that no bird passes when counting is impossible, by dropping them.

Rules checked on release: a weather stop is complete; a weather stop or an incomplete survey has a comment. A survey with linked bird records is never removed.

## Where decisions live

**Historical (1966–2021).** `raw/historical/count_2021.xlsx`, sheet `Pression observation`, columns `survey_complete`, `weather_stop`, `survey_comment`, matched by date and interval; a decision on a day-window row also reaches that day's hourly surveys inside it that have none of their own. Blank `survey_complete` is complete; blank `weather_stop` is no. Daily observer/weather narratives are retained separately. The columns replaced `survey_coverage` and `survey_coverage_comment` on 9 October 2026 (see the import record (local evidence: `docs/imports/survey-complete-2026-10-09/decisions.csv`)).

**Trektellen (2022–).** `config/survey-status/trektellen-survey-status.csv` and DEFILE tags in the header remarks. A CSV row without `datetime` applies to the whole header (`weather_stop = true`, `survey_complete = false`, or `survey_complete = remove` for an empty header that was no survey). A row with `datetime` is a timed weather stop (`weather_stop = true`) or, otherwise, an absence cut out of the header. `native_weather` and `native_remarks` guard against a changed source: a decision on a header whose text has changed is withheld and listed for review. Weather "HP" (hors protocole) intervals are weather stops when the remarks give their times. HP applying to a particular bird, taxon or a late observation does not change the survey.

**Historical gaps inside declared day windows.** `config/audit-settings/historical-gap-breaks.csv` lists absences (`date`, `datetime`, `note`) that are cut out of the inferred empty intervals; see below.

## Future recording

Use actual counting start/end times. Split sessions where practical; otherwise record the interruption in the remarks with a tag:

```text
[DEFILE weather]
Pas de comptage : pluie toute la journée.

[DEFILE weather from=10:00 to=12:30]
Brouillard entre 10h et 12h30, puis reprise.

[DEFILE absent from=12:00 to=13:30]
Pause repas, personne au poste.

[DEFILE incomplete]
Oiseaux passés non comptés : (expliquer).
```

Times are local Europe/Paris and must lie within the header. Without supported times, do not guess them from bird timestamps: describe the break in the remark, and the survey stays complete. Keep a rained-out day as a header without species, tagged `[DEFILE weather]`. Tags written before 9 October 2026 (`survey_coverage=... reason=...`) are still read: `none` is a weather stop (an absence with `reason=no_observer` or `logistics`), `partial` without times is complete, `unknown` is incomplete.

## Output and effort

Counts of a survey split by a weather stop or an absence move to the piece holding their own time; counts without a time of their own keep the day only (date-only `datetime`). Birds recorded in a weather stop or absence withhold that decision: the birds are kept, the survey stays counted, and the decision is listed for review (`birds_in_interruption`, `birds_in_weather_stop`). This applies to whole-header stops, to timed intervals with a bird clock inside, and to timed intervals covering the whole header while it has untimed birds. Every build checks that no released count is linked to a weather stop and that no two survey rows overlap. Malformed decision values in the CSV (anything but blank/`true` for `weather_stop`, blank/`false`/`remove` for `survey_complete`, or `survey_complete` on a timed row) stop the build.

The audit counts the union of complete intervals, weather stops excluded, as observed hours, and reports weather-stop intervals separately. A day with an incomplete survey has unknown observed hours. Calendar-day bounds are never hours. Original source hours remain in the internal tables.

## Historical empty intervals

The organiser clarified on 8 October 2026 that historical hourly recording omits hours without birds. Inside each declared `startTimeDay`–`endTimeDay` window, the build subtracts the union of native survey intervals and of counts timed over a range of their own (someone was counting then), and adds maximal uncovered intervals as complete under that continuity assumption. These additions use the historical S/N era IDs, contain no linked bird rows and invent no observer or weather measurements. Exact boundaries are retained, including partial hours and minute-scale gaps; point-derived hourly bins do not independently verify attendance.

Absences in `config/audit-settings/historical-gap-breaks.csv` are cut: no row. Long empty gaps remain explicitly assumed effort when no break is documented, not independently verified continuous observation. Known missing/deleted bird records make a survey incomplete rather than a zero-detection session.

Every added interval is checked for containment in its declared window, overlaps with other surveys, and the absence of counts linked to it or timed inside it. `output/audit/historical_effort_gaps.csv` traces additions (`added`) and cuts (`cut`) to source bounds; `empty_survey_review.csv` distinguishes explicit no-species markers, inferred empty intervals, minute boundaries, missing count data, weather stops and incomplete surveys. Dated decisions are in the historical-gap review (local evidence: `docs/reviews/historical-effort-gaps-2026-10-08/README.md`), the empty-effort follow-up (local evidence: `docs/reviews/empty-effort-2026-10-08/README.md`) and the 9 October move to survey_complete (local evidence: `docs/imports/survey-complete-2026-10-09/README.md`).
