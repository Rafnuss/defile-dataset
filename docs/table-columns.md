# Dataset column definitions


## Column dictionary

Generated from config/schema/datapackage.json; edit that source rather than these tables.

Frictionless validates standard types, constraints, primary keys and foreign keys. x-validationRules declare project rules implemented by the local validator; generic Frictionless validators do not enforce these extensions.

### count.csv

One row per count category and supported historical normal-count subgroup, with original source identity and timing. A row may represent several birds.

Primary key: `count_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

Foreign key: `survey_id` → `survey.survey_id`.

Foreign key: `taxon_id` → `taxonomy.taxon_id`.

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| count_id | string | Yes | unique: true | Readable release identity: era prefix (B notebook, S spreadsheet, N Naturalist, T Trektellen), local YYYYMMDD, optional recorded HHMM, eBird code or normalized original taxon label, optional collision/subgroup suffix, and normal/reverse/local category. Regenerated each build; corrections can change it. |
| source_count_id | string | Yes | — | Original source observation identity, shared by categories and subgroups. Historical workbook sheet/row or Trektellen dataid/export position; links to the internal source ledger. Not a unique key and not regenerated from the readable count ID. |
| survey_id | string | No | — | Original survey association, retained even when entry timing is missing or outside the survey interval. A link does not establish interval membership; explicit count datetime takes precedence over survey timing. Missing only when no released source survey is available. |
| taxon_id | string | Yes | pattern: "avibase-[A-F0-9]{8}" | Bird taxonomy foreign key. |
| datetime | string | Conditional | pattern: "([0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])&#124;[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)(/[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00))?)" | ISO local collection date, UTC datetime or UTC interval. Empty inherits survey timing; required when no survey is linked. Dates carry no invented midnight. String with an ISO pattern because date/datetime types cannot represent the permitted interval form. Z or +00:00 is required for clock times; the build writes Z. Calendar validity and ordering are checked by the declared ISO rule. |
| count | integer | Conditional | minimum: 0 | Numerical quantity for this count_category; required except for presence-only count_estimation=x. |
| count_category | string | Yes | enum: ["normal", "reverse", "local"] | normal: main migration direction; reverse: opposite direction; local: local/non-migrating birds (Trektellen Present). Missing reverse/local quantities produce no row; explicit zeros are retained. Filter normal for main migration totals. |
| count_estimation | string | No | enum: ["~", ">", "x"] | Recorded count qualifier. Blank means no recorded qualifier, not proof of exactness. Numeric totals retain the supplied number even when estimated or a lower bound. |
| age | string | No | enum: ["A", "1", "2", "3", "4", "I", "J", "S", "Non-Juv", "Non-adult", "non_adult", ">1y"] | Native Trektellen age code or the explicit historical lower-bound code >1y; see source crosswalk. Blank means no supported whole-row class. New codes require a dictionary review. |
| sex | string | No | enum: ["M", "F", "FC"] | Trektellen sex code; FC means female type, not necessarily female. Allowed codes are the reviewed inventory; unverified meanings are labelled explicitly. Blank means no supported whole-row class. New codes require a dictionary review. |
| plumage | string | No | enum: ["D", "L", "W", "I", "B", "E"] | Native or reviewed Trektellen plumage code; unknown codes remain native. Allowed codes are the reviewed inventory; unverified meanings are labelled explicitly. Blank means no supported whole-row class. New codes require a dictionary review. |
| remark | string | No | — | Residual source prose without field-name prefixes. Fully converted count/age/sex/plumage descriptions and explicit clocks are omitted; unresolved wording, behaviour and source-attributed daily context remain. Original fields are preserved in the internal source ledger. |
| remark_processing | string | No | — | Processing explanations, distinct from observer text. |
| trektellen_data_id | integer | No | minimum: 1 | Native count-entry dataid, not the survey-level countid. |

`count_estimation` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| ~ | Approximate/estimated numerical count. | — |
| > | More than the recorded number; a lower bound, not the inferred true total. | — |
| x | Presence without a numerical count; count must be empty. | — |

`age` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| A | Adult | display_verified |
| 1 | First calendar year | display_verified; Calendar age does not imply juvenile plumage; do not automatically convert to Batumi juv. |
| 2 | Second calendar year | display_verified |
| 3 | Third calendar year | numeric_convention; Observed native code; meaning extends the verified 1cy/2cy convention. Confirm full Trektellen dictionary. |
| 4 | Fourth calendar year | numeric_convention; Observed native code; meaning extends the verified 1cy/2cy convention. Confirm full Trektellen dictionary. |
| I | Older than first calendar year; immature | display_verified; The UI explicitly shows >1cy (imm); do not use for unspecified older birds or all non-adults. |
| J | Juvenile (provisional) | unverified; No code-to-label evidence recovered; preserve native values, no historical conversion to J yet. |
| S | Subadult | display_verified |
| Non-Juv | Non-Juv (native display label) | label_only; Precise definition unresolved; no automatic older-than-one-year conversion. |
| Non-adult | Non-adult (provisional) | unverified; Both spellings occur; the checked public page did not render the attribute. Preserve source spelling for now. |
| non_adult | Non-adult (provisional) | unverified; Both spellings occur; the checked public page did not render the attribute. Preserve source spelling for now. |
| >1y | Older than one year; adult status unspecified | literal_source_wording; Dataset extension, not a native Trektellen code. A lower bound in years is not an exact calendar age or an immature/adult classification. Exclude from adult/non-adult proportions. |

`sex` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| M | Male | display_verified |
| F | Female | display_verified |
| FC | Female type / female-coloured | display_verified; FC does not establish that the bird is female. |

`plumage` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| D | Dark morph | display_verified |
| L | Pale morph | display_verified |
| W | Unverified native W | unverified; Do not decode from the letter alone or infer a historical mapping. |
| I | Unverified native I | unverified; Do not decode from the letter alone or infer a historical mapping. |
| B | Unverified native B | unverified; Do not decode from the letter alone or infer a historical mapping. |
| E | Unverified native E | unverified; Do not decode from the letter alone or infer a historical mapping. |

Additional rules (declared in the descriptor):

- `datetime`: An unlinked count must supply its own date, datetime or interval.
- `count`: A numerical count is required unless count_estimation is x.
- `count`: Presence-only x must have an empty numerical count.
- `datetime`: Nonempty count timing is a valid ISO date, datetime or increasing interval; clock times must be UTC.

### survey.csv

Survey intervals: when someone was responsible for the count, including weather stops (complete, no bird). survey_complete says whether the counts hold every bird that passed.

Primary key: `survey_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| survey_id | string | Yes | unique: true | Readable release identity: era prefix (B notebook, S spreadsheet, N Naturalist, T Trektellen, C curated), local YYYYMMDD, recorded start HHMM where available, and optional collision suffix. Calendar-day closures omit time. Regenerated each build; corrections can change it. |
| source_survey_id | string | Yes | unique: true | Original internal survey identity, retained for joins to source audits and reviewed decisions. Trektellen native header ID remains in trektellen_count_id. |
| datetime | string | Yes | pattern: "[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)/[0-9]{4}-(0[1-9]&#124;1[0-2])-(0[1-9]&#124;[12][0-9]&#124;3[01])T([01][0-9]&#124;2[0-3]):[0-5][0-9](:[0-5][0-9](\\.[0-9]+)?)?(Z&#124;\\+00:00)" | UTC ISO interval. For curated day-precision closures, calendar boundaries identify an unavailable day, not effort hours. Native header timing is retained even when no counting occurred. |
| recording_era | string | Yes | enum: ["notebook", "spreadsheet", "naturalist", "trektellen", "curated"] | notebook, spreadsheet, naturalist or trektellen; historical 2021 is transitional. Curated identifies an added non-counting interval, not a native survey. |
| remark | string | No | — | Source survey prose and explicit no-species-entry annotation, including historical visitor/person-hour notes. |
| remark_processing | string | No | — | Processing notes; historical narratives have day-level scope. |
| trektellen_count_id | integer | No | minimum: 1 | Native header ID for the Trektellen correction link. |
| observers | string | No | — | Names/initials and attendance times as supplied; not quantitative observer effort. |
| weather | string | No | — | Recorded weather narrative, preserving changing conditions and qualifiers. |
| wind_speed_bft | integer | No | minimum: 0; maximum: 12 | Wind speed class on the Beaufort scale, 0 (calm) to 12 (hurricane force). Blank is unrecorded; zero can be a real calm reading. |
| wind_direction | string | No | enum: ["n", "nno", "no", "ono", "o", "ozo", "zo", "zzo", "z", "zzw", "zw", "wzw", "w", "wnw", "nw", "nnw", "var"] | Native Dutch compass code for the direction from which wind comes; standard 16-point compass plus variable. Codes are retained without translating the stored values. |
| cloud_cover | integer | No | minimum: 0; maximum: 8 | Cloud cover in eighths (oktas): 0 clear, 8 fully covered. Blank is unrecorded; zero can be a real clear-sky reading. |
| cloud_height | number | No | minimum: 0 | Native cloud-height value; units and default-zero semantics require confirmation. |
| precipitation | string | No | enum: ["geen", "regen", "mist"] | Reviewed native weather category, retained verbatim. Fog is recorded in this field despite not being precipitation. Blank is unknown; only geen explicitly records none. Other future categories require a dictionary review. |
| visibility | number | No | minimum: 0 | Visibility in metres, supported by the public display (e.g. 8000m). Native zero is retained and can be a default; it is not asserted to be measured zero visibility. |
| temperature | number | No | — | Temperature in degrees Celsius. Negative values are allowed. Native zeros are retained and may be defaults; no guessed meteorological bounds are imposed. |
| survey_complete | boolean | Yes | — | true: every bird that passed during the interval is in count.csv. This includes intervals when weather (rain, fog, storm) made counting impossible: no bird is assumed to pass (weather_stop). false: someone was counting but birds are known to have passed uncounted (records lost or deleted, birds noted as missed); rare. Times nobody was counting (absences, days not monitored) are not survey rows. |
| weather_stop | boolean | No | — | true: weather made counting impossible over the whole interval, so its zeros are assumed, not observed. Always with survey_complete true. Blank otherwise. Lets a user test the assumption that no bird passes when counting is impossible, by dropping these rows. |
| survey_comment | string | Conditional | — | Short note on the decision for this interval: why it is a weather stop or incomplete, what was cut out of it, or an assumption made. Not the observers' narrative, which stays in remark and weather. |

`wind_direction` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| n | North | standard_compass_interpretation |
| nno | North-northeast | standard_compass_interpretation |
| no | Northeast | standard_compass_interpretation |
| ono | East-northeast | standard_compass_interpretation |
| o | East | standard_compass_interpretation |
| ozo | East-southeast | standard_compass_interpretation |
| zo | Southeast | standard_compass_interpretation |
| zzo | South-southeast | standard_compass_interpretation |
| z | South | standard_compass_interpretation |
| zzw | South-southwest | standard_compass_interpretation |
| zw | Southwest | standard_compass_interpretation |
| wzw | West-southwest | standard_compass_interpretation |
| w | West | standard_compass_interpretation |
| wnw | West-northwest | standard_compass_interpretation |
| nw | Northwest | standard_compass_interpretation |
| nnw | North-northwest | standard_compass_interpretation |
| var | Variable direction | standard_compass_interpretation |

`precipitation` codes (empty cells remain missing):

| Code | Meaning | Evidence / notes |
| --- | --- | --- |
| geen | None (Dutch geen): explicit source category, not inferred from a blank. | — |
| regen | Rain (Dutch regen). | — |
| mist | Fog (Dutch mist), not drizzle; retained as a native weather category. | — |

Additional rules (declared in the descriptor):

- `datetime`: Survey timing is an increasing ISO datetime interval with UTC on both endpoints.
- `survey_complete`: A weather stop is a complete count with no bird.
- `survey_comment`: A weather stop says why in survey_comment.
- `survey_comment`: An incomplete survey says why in survey_comment.

### taxonomy.csv

One Avibase bird concept, with checklist names and the source-label crosswalk.

Primary key: `taxon_id`. Missing-value tokens: `[""]` (an empty string means an empty cell).

| Column | Type | Required | Constraints | Meaning |
| --- | --- | --- | --- | --- |
| taxon_id | string | Yes | unique: true; pattern: "avibase-[A-F0-9]{8}" | Avibase bird concept ID, including unidentified-bird groups. |
| scientific_name | string | No | — | AviList scientific name, with eBird/Clements fallback. |
| english_name | string | No | — | Checklist English name: AviList first, with eBird/Clements fallback. |
| taxon_rank | string | No | — | Checklist rank or group category; not all concepts are species. |
| order | string | No | — | Checklist order. |
| family | string | No | — | Checklist family. |
| parent_taxon_id | string | No | — | taxon_id of the smallest enclosing group in this table (a 'sp.' or slash taxon, or the species of a subspecies); empty for roots. Curated in taxonomy/parent_taxa.csv. Summing a group's descendants gives all birds counted under it. |
| taxonomy_source | string | No | — | Checklist and version used for the concept's scientific name. |
| ebird_code | string | No | — | Corresponding eBird/Clements code when available. |
| trektellen_species_id | string | No | pattern: "[1-9][0-9]*(,[1-9][0-9]*)*" | Distinct native species IDs, sorted numerically and comma-separated; empty for historical-only concepts. |
| source_taxa | array | Yes | — | JSON array of source names, native Trektellen species IDs, mapping notes and review labels. |

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
