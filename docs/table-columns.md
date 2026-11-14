# Dataset column definitions


## Column dictionary

Generated from config/schema/datapackage.json; edit that source rather than these tables.

Frictionless validates standard types, constraints, primary keys and foreign keys. x-validationRules declare project rules implemented by the local validator; generic Frictionless validators do not enforce these extensions. Age, sex and plumage are independent recorded attributes: no cross-field combination is prohibited, and one attribute must not be inferred from another. Release build checks additionally reject counts linked to weather stops and overlapping survey intervals; these cross-table/time rules are not enforced by validate_package alone. See docs/survey-coverage.md and docs/audit.md for assumptions and interpretation.

### Survey interpretation

survey_complete refers to birds accounted for within the recorded interval, not daily or seasonal coverage. Documented incomplete surveys are valid records, not unresolved audit findings.

Known unmonitored intervals are cut out. Missing survey dates remain unknown; do not zero-fill them.

Union of complete, non-weather-stop intervals within each Europe/Paris day. A day intersecting any incomplete survey has unknown observed hours. Weather-stop calendar bounds never contribute observed hours.

Within declared historical day windows, omitted empty hours are inferred as complete intervals under the organiser recording convention. Reviewed absences are cut out; no species zeros or observer/weather measurements are invented.

Missing dates and short days within reported season windows are coverage context, not warnings by themselves. Warnings concern unresolved status evidence; release failures concern inconsistent status, missing required explanations, counts linked to weather stops, and overlapping survey intervals.

### count.csv

One row per taxon, direction and survey entry: the number of birds counted. A row can hold many birds; historical entries described by age or sex are split into one row per class.

Primary key: `count_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

Foreign key: `survey_id` → `survey.survey_id`.

Foreign key: `taxon_id` → `taxonomy.taxon_id`.

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| count_id | string | Yes | unique: true | Readable row identifier: era letter (B notebook, S spreadsheet, N NaturaList, T Trektellen), local date YYYYMMDD, local clock HHMM when known, species code, and direction. It is rebuilt at each release and can change after corrections; do not use it as a permanent identifier. |
| survey_id | string | No | — | The survey (`survey.csv`) during which the birds were counted. |
| datetime | string | Yes | pattern: "([0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])&#124;[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)(/[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00))?)" | When the birds were counted, in UTC (ISO 8601): a time (`2023-09-15T08:12:00Z`), an interval (`start/end`), or a local date (`2023-09-15`) when only the day is known. An entry without a time of its own carries the interval of its survey. |
| taxon_id | string | Yes | pattern: "avibase-[A-F0-9]{8}" | The taxon (`taxonomy.csv`). |
| count | integer | Conditional | minimum: 0 | Number of birds. Empty only when `count_estimation` is `presence` (birds seen but not counted). |
| count_estimation | string | No | enum: ["approximate", "minimum", "presence"] | How the observer qualified the number. Empty: no qualifier was recorded (which does not prove the number is exact). |
| direction | string | Yes | enum: ["main", "reverse", "local"] | Which way the birds were moving. Use `main` for migration totals; `reverse` and `local` birds are counted separately and must not be added to them. |
| age | string | No | enum: ["adult", "first_calendar_year", "second_calendar_year", "third_calendar_year", "fourth_calendar_year", "after_first_calendar_year", "juvenile", "subadult", "not_juvenile", "not_adult"] | Age class given by the observer; empty when not recorded. Calendar years start on 1 January. Historical 'immature' and '> 1 an' are both `after_first_calendar_year`. |
| sex | string | No | enum: ["male", "female", "female_type"] | Sex given by the observer; empty when not recorded. `female_type` means female-looking, which includes young males of many species. |
| plumage | string | No | enum: ["dark_morph", "pale_morph", "winter", "immature", "breeding", "eclipse"] | Plumage or colour morph given by the observer; empty when not recorded. |
| remark | string | No | — | Observer's comment on the entry, as recorded (wording already turned into age, sex or time columns is removed). |
| remark_processing | string | No | — | Note added during processing, for example when a time was changed or removed. Not written by the observer. |
| trektellen_data_id | integer | No | minimum: 1 | Identifier of the entry on trektellen.org (2022 onward), for tracing it to the source. |

`count_estimation` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| approximate | The number is an estimate. | — |
| minimum | At least this many birds; the true number was higher. | — |
| presence | Birds were present but not counted; `count` is empty. | — |

`direction` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| main | Migrating in the main direction of autumn migration. | — |
| reverse | Flying in the opposite direction. | — |
| local | Local birds, not passing through (Trektellen 'present'). | — |

`age` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| adult | Adult | display_verified; General field usage: an individual judged to show adult plumage; age thresholds are species-specific and this is not a precise calendar-year class. EURING notes that age coding is based on plumage evidence, not known years of life.; EURING age 2; related_only; EURING 2 is full-grown with age otherwise unknown, which is broader than Trektellen Adult. EURING A means after fourth year and is not equivalent. |
| first_calendar_year | First calendar year | display_verified; Calendar-year age changes on 1 January and does not itself identify plumage; do not automatically convert to juvenile plumage.; EURING age 3; related_only; Both indicate first calendar year, but EURING 3 additionally specifies a full-grown bird; the EURING numeric code differs. |
| second_calendar_year | Second calendar year | display_verified; Calendar-year age changes on 1 January and does not itself identify plumage.; EURING age 5; calendar_year_equivalent; Both indicate second calendar year; the EURING numeric code differs. |
| third_calendar_year | Third calendar year | display_verified; Trektellen display confirms 3cy; verified by maintainer. This is a Trektellen code, not EURING age code 3. Calendar-year age changes on 1 January and does not itself identify plumage.; EURING age 7; calendar_year_equivalent; Trektellen 3cy matches EURING third-year concept; the EURING numeric code differs. |
| fourth_calendar_year | Fourth calendar year | display_verified; Trektellen display confirms 4cy; verified by maintainer. This is a Trektellen code, not EURING age code 4. Calendar-year age changes on 1 January and does not itself identify plumage.; EURING age 9; calendar_year_equivalent; Trektellen 4cy matches EURING fourth-year concept; the EURING numeric code differs. |
| after_first_calendar_year | Older than first calendar year (Trektellen '>1cy (imm)') | display_verified; English UI shows >1cy (imm); French UI shows >1 an for the same observations. Historical immature and > 1 an descriptors both map to I; original wording is retained in remarks. The combined code alone does not establish adult or non-adult status.; EURING age 4; related_only; Both indicate older than first calendar year with no exact year. Trektellen labels differ by language; the combined code does not establish maturity and is not a plumage code. |
| juvenile | Juvenile | display_verified; General ornithological usage defines juvenile plumage as the first true-feather plumage after down, commonly the plumage in which a young bird leaves the nest. Exact appearance and duration vary by species. This Trektellen age label is distinct from EURING Plumage Code J.; no_direct_age_code; Trektellen label Juvenile is confirmed. EURING has Plumage Code J for juvenile, but that is a different field; do not convert automatically to EURING age 3. |
| subadult | Subadult | display_verified; General ornithological literature uses subadult inconsistently for different age/plumage classes; treat this as an observer label without a universal year threshold.; no_direct_code; Subadult has no dedicated EURING age code; do not infer a calendar-year age. |
| not_juvenile | Not juvenile (Trektellen label; exact rule not documented) | label_only; Literal/general meaning is not juvenile, but the label does not specify whether this is based on plumage or calendar age. A bird can leave juvenile plumage while still in its first calendar year. Trektellen's precise rule is undocumented; do not infer age >1cy.; unresolved; Native display label is confirmed, but its precise definition is unresolved; no direct EURING age code assigned. |
| not_adult | Not adult (Trektellen label; exact rule not documented) | label_only; In general ornithological usage this is a broad complement of adult and may include juvenile and later immature stages; exact usage varies. Trektellen's precise inclusion rule is undocumented. Raw `non_adult` is normalized to `Non-adult` in released data.; unresolved; Display label confirmed; exact age-class criteria remain unresolved, so no direct EURING age code is assigned. |

`sex` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| male | Male | display_verified |
| female | Female | display_verified |
| female_type | Female-looking; the bird may be a female or a young male | display_verified; FC does not establish that the bird is female. |

`plumage` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| dark_morph | Dark morph | display_verified |
| pale_morph | Pale morph | display_verified |
| winter | Winter plumage | display_verified; Verified Trektellen meaning; retained as the native code. |
| immature | Immature plumage | display_verified; Plumage class, distinct from age I (>1cy, immature); do not force the two fields to agree. |
| breeding | Breeding plumage | display_verified; Verified Trektellen meaning; retained as the native code. |
| eclipse | Eclipse plumage (ducks) | display_verified; Verified Trektellen meaning; eclipse plumage applies to ducks. |

Additional rules (declared in the descriptor):

- `count`: A number is required unless count_estimation is presence.
- `count`: A presence row has no number.
- `datetime`: A valid ISO date, UTC time or increasing UTC interval.
- `remark`: `remark` is one line of text: no line break, tab or other control character, no leading or trailing space.
- `remark_processing`: `remark_processing` is one line of text: no line break, tab or other control character, no leading or trailing space.

### survey.csv

One row per survey: a period when someone was counting, or was on site but could not count because of the weather. Times when nobody was counting have no row; a date without a survey says nothing about the birds (it is not a zero).

Primary key: `survey_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| survey_id | string | Yes | unique: true | Readable survey identifier: era letter (B notebook, S spreadsheet, N NaturaList, T Trektellen, C curated), local date YYYYMMDD and local start HHMM when known. Rebuilt at each release; it can change after corrections. |
| datetime | string | Yes | pattern: "[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)/[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)" | Start and end of the survey in UTC, as an ISO 8601 interval (`start/end`). For a whole-day weather stop with no recorded hours, the interval is the local calendar day; it is not counting time. |
| recording_era | string | Yes | enum: ["notebook", "spreadsheet", "naturalist", "trektellen", "curated"] | How the counts were recorded: `notebook` (1966-2013, daily totals), `spreadsheet` (2014-2016, mostly hourly), `naturalist` (2017-2021, NaturaList entries), `trektellen` (2022 onward, trektellen.org), or `curated` (a weather stop added from the reports, outside the recorded surveys). |
| survey_complete | boolean | Yes | — | `true`: every bird that passed during this survey is in `count.csv`. `false`: birds are known to have passed uncounted (records lost, birds missed); `survey_comment` says why. It describes this interval only, not the whole day. |
| weather_stop | boolean | No | — | `true`: the weather (rain, fog, storm) made counting impossible during the whole interval. No bird is assumed to have passed; no count is linked to it. Exclude these intervals from counting hours. `false` otherwise. |
| survey_comment | string | Conditional | — | Why a survey is incomplete or a weather stop, or what was assumed when the interval was rebuilt. Written during processing; observers' own words are in `remark` and `weather`. |
| observers | string | No | — | The people present, comma-separated: names or initials as recorded, with reviewed spelling variants merged. Attendance hours, groups and unreadable fragments are left out. |
| weather | string | No | — | Weather as described by the observers. |
| temperature | number | No | — | Temperature in °C. Trektellen's form writes 0 when the field is left unanswered, so a Trektellen 0 is left empty. |
| wind_speed_bft | integer | No | minimum: 0; maximum: 12 | Wind speed on the Beaufort scale, 0 (calm) to 12. Empty: not recorded. |
| wind_direction | string | No | enum: ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW", "variable"] | Direction the wind blows from (16-point compass), or `variable`. |
| cloud_cover | integer | No | minimum: 0; maximum: 8 | Cloud cover in eighths (oktas): 0 clear sky, 8 overcast. Empty: not recorded. |
| cloud_height | number | No | minimum: 0 | Cloud height as entered on Trektellen; the unit is not confirmed. Trektellen's form writes 0 when the field is left unanswered, so a 0 is left empty. |
| precipitation | string | No | enum: ["none", "rain", "fog"] | Rain or fog as recorded. Empty means not recorded; only `none` says there was none. |
| visibility | number | No | minimum: 0 | Visibility in metres. Trektellen's form writes 0 when the field is left unanswered, so a Trektellen 0 is left empty. |
| remark | string | No | — | Observers' comments on the survey. |
| remark_processing | string | No | — | Note added during processing. Not written by the observers. |
| trektellen_count_id | integer | No | minimum: 1 | Identifier of the survey on trektellen.org (2022 onward), for tracing it to the source. |

`wind_direction` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| N | North | — |
| NNE | North-northeast | — |
| NE | Northeast | — |
| ENE | East-northeast | — |
| E | East | — |
| ESE | East-southeast | — |
| SE | Southeast | — |
| SSE | South-southeast | — |
| S | South | — |
| SSW | South-southwest | — |
| SW | Southwest | — |
| WSW | West-southwest | — |
| W | West | — |
| WNW | West-northwest | — |
| NW | Northwest | — |
| NNW | North-northwest | — |
| variable | Variable direction | — |

`precipitation` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| none | No rain or fog. | — |
| rain | Rain. | — |
| fog | Fog. | — |

Additional rules (declared in the descriptor):

- `datetime`: Survey timing is an increasing ISO datetime interval with UTC on both endpoints.
- `survey_complete`: A weather stop is a complete count with no bird.
- `survey_comment`: A weather stop says why in survey_comment.
- `survey_comment`: An incomplete survey says why in survey_comment.
- `survey_comment`: `survey_comment` is one line of text: no line break, tab or other control character, no leading or trailing space.
- `observers`: `observers` is one line of text: no line break, tab or other control character, no leading or trailing space.
- `weather`: `weather` is one line of text: no line break, tab or other control character, no leading or trailing space.
- `remark`: `remark` is one line of text: no line break, tab or other control character, no leading or trailing space.
- `remark_processing`: `remark_processing` is one line of text: no line break, tab or other control character, no leading or trailing space.

### taxonomy.csv

One row per taxon counted: a species, a subspecies, or a group used when the bird could not be identified to species (for example 'buzzard sp.').

Primary key: `taxon_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| taxon_id | string | Yes | unique: true; pattern: "avibase-[A-F0-9]{8}" | Avibase identifier of the taxon; `count.csv` links to it. |
| scientific_name | string | No | — | Scientific name (AviList; eBird/Clements when AviList has none). |
| english_name | string | No | — | English name (AviList; eBird/Clements when AviList has none). |
| taxon_rank | string | No | — | Rank: `species`, `subspecies`, or a group of uncertain identification (`spuh`: genus or family only; `slash`: one of two species; `hybrid`; `domestic`). |
| parent_taxon_id | string | No | — | `taxon_id` of the smallest group that contains this taxon (the species of a subspecies, or a 'sp.' or slash group); empty at the top. Adding a group's descendants gives every bird counted under it. |
| order | string | No | — | Order. |
| family | string | No | — | Family. |
| systematic_count_start_year | integer | No | minimum: 1966 | First year this taxon was counted systematically. From that year, a complete survey with no row for it can be read as zero birds; before it, a missing row means unknown. Empty: no start year set. |
| taxonomy_source | string | No | — | Checklist and version that gave the scientific name. |
| ebird_code | string | No | — | eBird species code, when there is one. |
| trektellen_species_id | string | No | pattern: "[1-9][0-9]*(,[1-9][0-9]*)*" | Trektellen species identifier(s), comma-separated; empty for taxa only in the historical records. |

### report_text.csv

Accepted French report prose indexed by year, category and key, read from raw/reports/report_text.csv. Species keys are dataset Avibase IDs, including broader taxon concepts. Shared passages are not independent evidence; missing rows do not imply absence. Extraction history is archived and is not part of the build.

Primary key: `['year', 'category', 'key']`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| year | integer | Yes | — | Report year. |
| category | string | Yes | enum: ["species", "site", "monitoring", "weather", "results", "outreach"] | Account category. Together with year and key, identifies one populated account. |
| key | string | Yes | pattern: "^(avibase-[A-F0-9]{8}&#124;background&#124;methods&#124;effort&#124;nocturnal&#124;season&#124;july&#124;august&#124;september&#124;october&#124;november&#124;december&#124;overview&#124;highlights&#124;discussion&#124;activities)$" | For category species, an Avibase taxon_id from taxonomy.csv. Otherwise a key allowed for the category, as documented below. Weather uses season or an English month name. The year is the report year, including when prose compares earlier years. |
| text | string | Yes | — | Non-empty curated French report prose, preserving paragraph breaks. |

`category` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| species | Taxon accounts; key is an Avibase ID in taxonomy.csv, including species, spuh, slash and hybrid concepts. | — |
| site | Site history, geography and organisational background. Allowed key: background. | — |
| monitoring | Monitoring protocol, actual effort/coverage and nocturnal monitoring. Allowed keys: methods, effort, nocturnal. | — |
| weather | Weather and visibility narrative. Allowed keys: season, july, august, september, october, november, december. | — |
| results | Seasonal results and interpretation. Allowed keys: overview, highlights, discussion. | — |
| outreach | Public engagement, school activities and visitor communication. Allowed key: activities. | — |

`key` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| background | Site history and geography. | category = site |
| methods | Field protocol followed by data processing and analysis, with internal headings. | category = monitoring |
| effort | Actual dates/hours, staffing, volunteer availability, coverage gaps and observation-point changes. | category = monitoring |
| nocturnal | Acoustic/nocturnal monitoring methods, effort, results and limitations; separate from daytime visual counts. | category = monitoring |
| season | Season-wide weather and visibility. | category = weather |
| july | July weather and visibility. | category = weather |
| august | August weather and visibility. | category = weather |
| september | September weather and visibility. | category = weather |
| october | October weather and visibility. | category = weather |
| november | November weather and visibility. | category = weather |
| december | December weather and visibility. | category = weather |
| overview | Broad seasonal totals, composition and migration patterns. | category = results |
| highlights | Notable events, mixed-species observations, irruptions and records. | category = results |
| discussion | Interpretation, longer-term trends, limitations and outlook. | category = results |
| activities | School activities, public events, visitor attendance and outreach restrictions. | category = outreach |

Additional rules (declared in the descriptor):

- `key`: Species accounts must use Avibase taxon IDs.
- `key`: Allowed keys for site: background.
- `key`: Allowed keys for monitoring: methods, effort, nocturnal.
- `key`: Allowed keys for weather: season, july, august, september, october, november, december.
- `key`: Allowed keys for results: overview, highlights, discussion.
- `key`: Allowed keys for outreach: activities.
- `key`: Every species account key must exist in taxonomy.taxon_id.

### paper_text.csv

Accepted French species accounts from all four Nos Oiseaux papers, read from raw/reports/paper_text.csv. Same category/key/text structure as report_text; source_id distinguishes the two 1996 parts and multi-year syntheses. Species keys follow existing Avibase mappings; three group keys retain shared accounts. Missing accounts do not imply absence. Extraction evidence is archived.

Primary key: `['source_id', 'category', 'key']`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| source_id | string | Yes | enum: ["defile-paper-1996-I", "defile-paper-1996-II", "defile-paper-2019", "defile-paper-2020"] | Paper identity (the local reference library lists the documents): 1996 Parts I and II describe 1993; 2019 covers 1993–2017; 2020 covers 1993–2019. |
| category | string | Yes | enum: ["species"] | Account category; currently species accounts only. |
| key | string | Yes | enum: ["avibase-00DA9D91", "avibase-06D9A2C8", "avibase-082F3A63", "avibase-1078FFEA", "avibase-1327AC55", "avibase-166CD440", "avibase-22647E26", "avibase-27903EF7", "avibase-28825494", "avibase-2D52E3A5", "avibase-2DAB45B8", "avibase-2DABF98F", "avibase-3395DCF1", "avibase-39086887", "avibase-3BB5CBA6", "avibase-3C0C325D", "avibase-3DF5C587", "avibase-451D6FC8", "avibase-47E58408", "avibase-49D9148A", "avibase-4B8CC285", "avibase-4E6EF3F9", "avibase-56FB47C0", "avibase-5A3D91D3", "avibase-5D1987CE", "avibase-5EAB32D3", "avibase-5F8E7CA8", "avibase-6364E4A5", "avibase-63B6412E", "avibase-6429024D", "avibase-65BD2033", "avibase-66AA3934", "avibase-68E4C0D1", "avibase-6F2AF9D0", "avibase-742EC2F1", "avibase-760F307A", "avibase-8372FFBA", "avibase-84E1F114", "avibase-89C42590", "avibase-90B13ACF", "avibase-94A44032", "avibase-95DD1855", "avibase-97C47F3E", "avibase-9820CECA", "avibase-997A9437", "avibase-99B8841E", "avibase-9BE53D34", "avibase-A635F565", "avibase-A8A85BCF", "avibase-BC06BC0D", "avibase-CE71B4FF", "avibase-D4C32F8E", "avibase-D8D10F2C", "avibase-D9B001DF", "avibase-DB376A66", "avibase-E074D706", "avibase-E15BC0CB", "avibase-E2817DAE", "avibase-E2A19474", "avibase-E91E287A", "avibase-ED2AC04E", "avibase-ED5A7E8F", "avibase-F029489A", "avibase-F3DA111C", "avibase-F558C7F9", "avibase-FA1CAD29", "avibase-FA2F9125", "avibase-FB02DD96", "group-aigle-pomarin-criard", "group-corbeau-freux-choucas-des-tours", "group-hirondelles-rustique-fenetre-rivage"] | Accepted Avibase taxon concept or shared group key. Group keys cover freux/choucas, three swallow species, and pomarin/criard eagles. Paper taxa can be absent from the count taxonomy; historical names and mapping notes remain in the extraction archive. |
| text | string | Yes | — | Curated French prose with paragraph breaks, including published status and summary statistics where present. Figures and tables omitted; published discrepancies retained. |
