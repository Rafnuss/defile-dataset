# Survey coverage and observed effort

The build discovers paired annual data/header exports in `raw/trektellen`. Add the next year's files and run `uv run python scripts/build_dataset.py`.

## Definition

`survey_coverage` describes systematic observation inside each survey's start/end:

| Value | Meaning |
| --- | --- |
| complete | Counting throughout the stated interval, including zero detections. |
| partial | Counting during some but not all of the interval. |
| none | No counting; no positive or presence-only counts attributed to it. |
| unknown | Coverage cannot be established from available records. |

Complete coverage is independent of daily coverage and protocol compliance. Recorded count/no-species intervals are assumed complete unless comments or reviewed sources establish interruptions. A short empty header may represent a genuine zero session when the surrounding event/checklist pattern supports that interpretation. Missing dates alone do not establish non-counting.

## Existing data

Historical decisions are stored in `count_2021.xlsx`, `Pression observation`, matched by date and interval. Daily observer/weather narratives are retained separately. Trektellen decisions are maintained in `config/survey-status/trektellen-survey-status.csv`. The original weather and remarks remain unchanged; changed source snapshots require review. The config contains whole-header classifications and explicit non-counting gaps. Gap boundaries describe non-counting, never invented observed effort.

Historical additions inside declared day windows use the same `survey_coverage` vocabulary. Their interval exceptions are in `config/audit-settings/historical-gap-breaks.csv`: the filename is retained, but its explicit `survey_coverage` column supports unknown attendance conflicts as well as none breaks. Complete empty intervals are inferred under the organiser's omitted-hour convention; minute boundary gaps and long unsupported intervals carry separate explanations. See the empty-effort review (local evidence: `docs/reviews/empty-effort-2026-10-08/README.md`). `survey_status_review.csv` now uses released survey IDs alongside `source_survey_id`, and includes unresolved added intervals. It remains the established filename; no `survey_status` column is reintroduced.

Weather HP intervals are interpreted as interrupted systematic counting when comments and event clocks support that pattern. HP applying to a particular bird, taxon or a late observation does not change coverage of the earlier survey. Outside-season counts can be complete. Attendance notes are not assumed exhaustive when recorded count or no-species intervals establish observation beyond those notes.

Use brief `survey_coverage_comment` explanations for important assumptions or missing information. No separate protocol category or additional review ledger is needed.

## Future recording

Use actual counting start/end times. Split sessions where practical; otherwise record an interruption in remarks. Keep documented non-counting headers without species zeros.

```text
[DEFILE survey_coverage=none reason=weather]
Pas de comptage : pluie toute la journée.

[DEFILE survey_coverage=partial reason=weather]
Comptage interrompu ; heures exactes inconnues.

[DEFILE survey_coverage=none reason=weather from=10:00 to=12:30]
Interruption entre 10h et 12h30, puis reprise.
```

The last tag describes a non-counting interval inside the header and makes the whole header partial. Both endpoints are required, local Europe/Paris, within the header. Without supported times, use partial and explain the interruption without guessing boundaries from bird timestamps. Complete and unknown are also accepted tag values.

## Output and effort

The release exports only `survey_coverage` and `survey_coverage_comment` for coverage. Known gaps outside headers can create separate none records; no zero species counts are generated. Positive/presence-only birds contradicting none change coverage to unknown and remain retained for review.

The audit counts complete intervals as effort under the stated continuity assumption. Known gaps are subtracted from partial intervals. Partial intervals without usable gap boundaries and unknown intervals make the day's observed hours unknown rather than turning their full header spans into counting effort. Calendar bounds for none are never effort. Original source hours remain in the internal tables.

## Historical empty intervals

The organiser clarified on 8 October 2026 that historical hourly recording omits hours without birds. Inside each declared `startTimeDay`–`endTimeDay` window, the build subtracts the union of native survey intervals and adds maximal uncovered intervals as complete under that continuity assumption. These additions use the historical S/N era IDs, contain no linked bird rows and invent no observer or weather measurements. Exact boundaries are retained, including partial hours and minute-scale gaps; point-derived hourly bins do not independently verify attendance.

Reviewed exceptions in `config/audit-settings/historical-gap-breaks.csv` split inferred non-counting breaks and intervals with unresolved attendance conflicts. Long empty gaps remain explicitly assumed effort when no break is documented, not independently verified continuous observation. Known missing/deleted bird records remain unknown coverage rather than zero-detection sessions. Unknown intervals make their days' observed-effort denominator unknown.

Every added interval is checked for containment in its declared window, overlaps with other surveys and absence of linked counts. `output/audit/historical_effort_gaps.csv` traces additions to source bounds; `empty_survey_review.csv` distinguishes explicit no-species markers, inferred empty intervals, missing counts and non-counting. Dated decisions are in the historical-gap review (local evidence: `docs/reviews/historical-effort-gaps-2026-10-08/README.md`) and the empty-effort follow-up (local evidence: `docs/reviews/empty-effort-2026-10-08/README.md`).
