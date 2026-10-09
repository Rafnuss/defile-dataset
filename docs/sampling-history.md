# Sampling history and temporal resolution

Methods review, 7 October 2026; updated 8 October 2026 with both recovered 1996 papers. This is evidence for the next audit, not a new cleaning policy. Read the methods/coverage sections of the two central papers and available annual reports; scanned methods pages were checked with French OCR and selected page images. Species accounts have not all been reconciled. Page references below are **PDF pages**; printed page numbers are given for the scientific papers. The library is indexed in references/sources.csv (local evidence: `references/sources.csv`).

## What changed over time

| Era | Evidence | Implication for the audit |
| --- | --- | --- |
| 1966–1992 | 2019 paper, pp. 1–3 (printed 101–103): intermittent coverage initially; 1966 had 21 days/90 hours. Daily coverage developed unevenly; historical daily forms were digitised later. | Do not infer a full season, continuous daily coverage, or hourly detail from a dated count. |
| 1993 | Charvoz, Matérac & Maire (1996), PDF pp. 4–7 (printed 264–267): counts entered every 15 minutes; 17 July–14 November, 100 observation days/719 hours; eight dated days without observers and 13 undated days of continuous rain. Published clocks are GMT+1 (winter time). | Fine field recording existed in 1993, but its survival in digitised records is unverified. Do not assign quarter-hour resolution or summer civil time to current workbook rows from this paper alone. |
| 1994–2007 | 2019 paper, pp. 2–3: systematic seasonal counting from 1993, volunteers, daily forms digitised retrospectively. The 2004–2007 reports are short summaries and discuss weather losses. | Distinguish season calendar days from days actually counted. Exact source start/end times need verification against original forms/effort records. |
| 2008–2016 | 2019 paper p. 3; reports 2008–2010 pp. 6–7, 2011 pp. 8–9, 2012 pp. 8–10, 2013 pp. 9–11, 2014/2016 pp. 8–9: salaried staff with volunteers; minimum summer hours about 10–17 and autumn 9–16; often longer. Daily data entry after counting and hourly weather notes. | Hourly weather does not establish hourly count resolution. Minimum protocol hours are not each day's actual effort. Count-day duration differs from person-hours. |
| 2017–2021 | 2019 paper p. 3: live NaturaList entry by staff from 2017, volunteers still entering later. Reports 2019 p. 9, 2020 pp. 8–9, 2021 pp. 9–10 explicitly describe live staff entries and hourly paper records for volunteers. | Mixed point/interval/day resolution is expected. The 2017 report repeats older minimum hours whereas the retrospective paper describes expanded 2017 hours: preserve the disagreement. |
| 2022 | Full annual report unavailable; preliminary newsletter and native exports available. | No detailed protocol claim from the newsletter alone. Native export structure is evidence of data resolution, not proof of the field protocol. |
| 2023 | Report pp. 10–11: sunrise–19:30 until 10 August, then sunrise–sunset; Trektellen entry. Extra dates outside the official season are recorded. P. 7 describes occasional use of Vulbens cemetery in fog. | Preserve off-protocol counts and alternate station evidence; match the report's selected dates before reconciling. |
| 2024 | Report pp. 10–12: sunrise–18:00 until 31 July, then sunrise–sunset; two uncounted weather days inside the official season and extra counts before it. | A season described as 124 days is not 124 observed full days. Start/end envelopes alone cannot prove uninterrupted coverage. |
| 2025 | Report pp. 9–10: sunrise–sunset, 18 July–18 November; 23 October not counted because of wind, with some other hours outside protocol because of fog/rain. | Preserve actual effort and interruptions; do not reconstruct effort from daylight or nominal protocol. |

The 2019 paper p. 3 describes individual counting of raptors/large birds, estimation of pigeon flocks and half-hour estimation for passerines. The 2020 paper p. 1 (printed 221) warns that recording of other groups depends on observer interest. Neither a day with no entry nor an empty hour establishes a taxon absence without verified recording scope.

**An “hourly” rate can be calculated from daily data.** The 2019 paper p. 3 and 2020 paper p. 2 describe daily counts normalised by daily observation duration. These rates are not observations allocated to individual clock hours.

**Comparison periods differ.** The 2019/2020 scientific papers use 18 July–18 November for common coverage; reports 2019–2020 describe 15 July–20 November for some comparisons, and recent reports use 18 July–18 November. Reports 2024–2025 combine Wood Pigeon with unidentified pigeons in comparison graphs. Date boundaries and taxon grouping must be recorded for each reference total rather than imposed globally.

**Effort units differ.** Report 2013 pp. 10–11 reports roughly 1,200 observation hours and 3,400 observer-hours. Two observers for ten hours contribute ten elapsed hours and twenty person-hours. Neither measure can be substituted for the other.

**Direct evidence for 1993.** The recovered 1996 paper describes quarter-hour field counts (PDF p. 4), unlike the day-level resolution that survives in early cleaned data. Its GMT+1 clock convention (PDF p. 7, footnote) must be checked against original forms before any historical time correction. The 17 July–14 November season also differs from the later common comparison window. The wording about whole observation days on p. 4 coexists with rain interruptions on p. 5; it does not prove 100 uninterrupted full days. The study reports eight observer absences on 13, 16, 17, 18, 20, 21 and 31 August and 3 September; the other 13 rain days are undated. Preserve these as publication evidence until matched to native records.

**Part II scope and estimates.** Matérac, Charvoz & Maire (1996), PDF pp. 1–6 (printed 389–394), confirms the same 1993 season. Table 1 separates southwest and northeast movements of cormorants and gulls; these must remain separate, without automatic subtraction. Skylark is reported as >2,049, not an exact total. Swallows were estimated by counting one minute per quarter hour and extrapolating, yielding at least 130,000 birds across several species. The station could not see the Rhône, limiting detection of low-flying waterbirds; other taxa were not systematically counted. The paper also reports recorded weather in Part I and explains movements in Part II, whereas the organiser notes below say nothing was recorded before 2008: retain this conflict for clarification about original notes versus standardised forms or surviving data. See the Part II review (local evidence: `docs/reviews/1996-paper/part-II.md`).

## What survives in the received data

In the local research checkout, run `uv run python scripts/review/profile_temporal_resolution.py`. Diagnostic outputs go to `interim/diagnostics/temporal-profile/`; no rows or times are changed. Counts include raw taxa and unreviewed periods and are not publication totals.

- The manually cleaned historical workbook has day-window-sized records through 2013 and mostly shorter intervals from 2014 onward. Shorter intervals have a median of 60 minutes. Some original entry clocks survive in later years.
- No date in that cleaned historical baseline mixes day-window-sized and partial-day rows. This does not disprove mixed recording: earlier manual deletions may have removed that evidence. The audit must return to the original workbooks, not only `count_2021.xlsx`.
- Trektellen periods are predominantly long day windows in 2023–2025, while entries have optional times. In 2025, 442 entries have no time, with a raw `direction1` sum of 7,385. They must remain eligible for daily totals. An untimed entry is a limitation on hourly analysis, not by itself a reason to exclude the birds.
- “Same as day window” is a diagnostic classification, not a verified precision label. A recorded point time may be entry time rather than passage time. These semantics need source documentation and organiser review.

Organiser clarification in this conversation (7 October 2026): a day-level entry alongside hourly entries is an **additional count without an hour**, not a summary including those entries. Preserve that rule in ingestion; distinguish separately any genuine daily summary rows used as reference totals.

## Recording systems in the received inputs

| Era | Coverage in the received inputs | Interpretation |
| --- | --- | --- |
| Notebook (B) | Historical sheet `1966-2013` | Retrospectively digitised daily records. “Notebook” is a working era label, not verified original medium for every row. |
| Spreadsheet (S) | Historical sheet `2014-2016` | Digitised forms, mainly hourly intervals; some daily records. |
| NaturaList (N) | Historical sheet `2017-2021` | Mixed live entry, intervals and daily forms. Trektellen began in 2021, so this received sheet is a transition-era source, not proof every entry came from NaturaList. |
| Trektellen (T) | Native exports read from 2022 onward | Count headers plus timestamped or untimed entries. The separate 2021 export is archived but not added a second time. |

Era letters above are the current readable record-ID prefixes, not the original internal survey/observation IDs. Curated survey additions use C; see [dataset usage](dataset.md).

## Original organiser notes

The following French notes preserve the organiser evidence behind the timeline; publication evidence and received-file resolution are distinguished above.

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

Nous avions saisit les données 1966-2007 du Dr Charvoz en décryptant au mieux ses fiches (écriture de médecin !) mais des infos se sont perdues. Certains observateurs comme Lutz Lücker ont des souvenirs mémorables de migration des pigeons dont nous n'avons pas trace.

#### Data collection

- de 2008 à 2016 on avait des fiches papiers standard pour noter par heure (heure locale), c'était donc saisie avec des totaux horaires. pour certaines journées il y a seulement un formulaire avec total jour
- de 2017 à 2020 on a de l'ultra-brute car saisie en direct avec Naturalist. donc pas d'heure de début et de fin de suivi dans les données (mais on a ça à coté), seulement l'heure de la saisie de la donnée, donc à quelques minutes près celle du passage des oiseaux "en majorité" car ce mode de saisie était appliqué la semaine par les spotteurs pour les journées assurées par les bénévoles il y a seulement un formulaire avec total jour.
- depuis 2021 on utilise l'appli Trektellen, faite pour le suivi de migration.

Current timing/selection rules are in [processing](processing.md), observed effort in [survey coverage](survey-coverage.md), and the implemented export in [GBIF](gbif.md). The full 2022 report, original forms/clocks and matched source-to-report totals remain evidence gaps; see the 1996 review (local evidence: `docs/reviews/1996-paper/README.md`).
