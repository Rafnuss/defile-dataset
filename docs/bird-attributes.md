# Age, sex and plumage: historical data to Trektellen

First implementation, 7 October 2026. Trektellen is the target vocabulary because it is the ongoing collection system. Batumi Table 3 provides a secondary comparison, not a replacement vocabulary. Historical counts are split into their described subgroups and an undescribed remainder. The source total is preserved; no attributes are inferred for the remainder.

## Where the information lives

| Recording era | Received field | Evidence and limits |
| --- | --- | --- |
| Notebook/digitised daily data, 1966–2013 | detail: 1,121 recovered rows, from 2001 onward | Imported once from Alldata into count_2021.xlsx using unique species/date/count matches. Corrected reference times retained. Marginal counts/proportions are derived summaries, not extra observations. |
| Spreadsheet/forms, 2014–2016 | detail: 550 non-empty rows | Structured quantity/description text, often several components per count. No separate historical plumage column. |
| NaturaList/transition, 2017–2021 | details: 6,639 non-empty rows | Similar quantity/description text. Entry clocks are separate from bird attributes. The received sheet includes a transition to Trektellen in 2021, so its label does not prove every record's original platform. |
| Trektellen exports, 2022–2026 | age, sex, plumage | Native structured fields: 12,498 age entries, 3,991 sex entries and 141 plumage entries in the inspected snapshots. Values are preserved except `non_adult`, which is normalized to the single released code `Non-adult`. |

The original historical exports (`data_brute_DE_2014_2021.xlsx`, `data_défilé_2016.xlsx`, `data_défilé_2020.xlsx`) retain Détails text rather than separate age/sex/plumage fields. The one-off import log (local evidence: `docs/imports/alldata-2026-10-07/README.md`) documents the earlier recovery. The historical build now reads only count_2021.xlsx; archived workbooks are not dependencies. The published four-table schema omits historical_in_list and trektellen_group_id as requested; the originals remain archived.

## Trektellen target dictionary and evidence

The authoritative code definitions and enum constraints are in [config/schema/datapackage.json](../config/schema/datapackage.json). The evidence dictionary [bird_attribute_codes.csv](bird_attribute_codes.csv) is generated from it. It records the native code, meaning, evidence status, example native data ID, evidence source, and Batumi and EURING comparisons. This is an inventory of codes observed in our files, not a claim that the entire Trektellen vocabulary has been recovered.

Age and sex meanings were checked against public English count tooltips and matched to the native export by site/date, species, minute and numerical direction/local component where available. The dataset maintainer also confirmed Trektellen's 3cy, 4cy and Juvenile menu labels on 12 October 2026; the attached age-menu screenshot also shows Adult, 1cy, >1cy (imm), 2cy, Non-Juv, SubAd and Non-adult. Plumage W, I, B and E meanings were confirmed by the maintainer on Trektellen on the same date. Examples include the [1 October 2026 count](https://www.trektellen.org/count/view/2422/20261001?language=english), [30 July subadult](https://www.trektellen.org/count/view/2422/20260730?language=english), [19 September dark morph](https://www.trektellen.org/count/view/2422/20260919?language=english) and [27 September pale morph](https://www.trektellen.org/count/view/2422/20260927?language=english). The public label and original native code are separate pieces of evidence.

| Attribute | Native code | Established meaning | Treatment |
| --- | --- | --- | --- |
| Age | A | Adult | Historical adult expressions can map directly. |
| Age | 1, 2 | First, second calendar year (1cy/2cy) | Map explicit historical calendar-year expressions. |
| Age | 3, 4 | Third and fourth calendar year (3cy/4cy) | Confirmed in Trektellen's age menu by the dataset maintainer on 12 October 2026. |
| Age | I | >1cy (imm) in the public UI | Historical immature and > 1 an labels both map to I; retain the original wording in remarks. This combined class does not establish maturity. |
| Age | S | SubAd | Confirmed public display; no matching historical phrase yet. |
| Age | J | Juvenile | Confirmed in Trektellen's age menu by the dataset maintainer on 12 October 2026. |
| Age | Non-Juv | Public label Non-Juv | Literally signals not juvenile, but the criterion (plumage or age) is undocumented; do not automatically equate it with calendar age >1. |
| Age | Non-adult / non_adult | Non-adult | General usage is a broad complement of adult; Trektellen's exact inclusion rule remains undocumented. The pipeline normalizes the two source spellings to `Non-adult`. |
| Sex | M, F | Male, female | Historical unambiguous expressions map directly. |
| Sex | FC | Female type | Includes birds not positively sexed female. Map type femelle to FC, never F. |
| Plumage | D, L | Dark morph, pale morph | Confirmed public display; no explicit historical morph descriptor found in the current dedicated detail fields. |
| Plumage | W | Winter plumage | Meaning confirmed on Trektellen; preserve the native code. |
| Plumage | I | Immature plumage | Meaning confirmed on Trektellen; this is independent of age code I. |
| Plumage | B | Breeding plumage | Meaning confirmed on Trektellen; preserve the native code. |
| Plumage | E | Eclipse plumage (ducks) | Meaning confirmed on Trektellen; preserve the native code. |

## General ornithological definitions and remaining limits

Trektellen confirms the labels, but does not provide a definition for every class. The definitions below use broader ornithological conventions as context; they do not claim undocumented Trektellen rules. Age, plumage, moult stage and sexual maturity are related but distinct concepts. In particular, a calendar-year class does not determine which plumage a bird is wearing.

| Trektellen age value | General definition or convention | What can safely be concluded here |
| --- | --- | --- |
| A — Adult | A bird judged to show adult plumage. The plumage at which a species is considered adult and the age when it is acquired vary by species; this is not a universal year-of-life threshold. | Keep as the observer's adult class. Do not convert to EURING age A, which means after fourth-year. |
| 1 — 1cy | First calendar year: from hatching through 31 December of the hatch year. | Calendar-year class only; not synonymous with juvenile plumage. |
| 2 — 2cy | Second calendar year: 1 January through 31 December after the hatch year. | Calendar-year class only; not synonymous with immature or adult plumage. |
| 3 — 3cy | Third calendar year. | As above. Trektellen label confirmed by the maintainer. |
| 4 — 4cy | Fourth calendar year. | As above. Trektellen label confirmed by the maintainer. |
| I — >1cy (imm) | Trektellen combines these labels: English >1cy (imm), French >1 an. | Historical immature and > 1 an map to I. Preserve the original descriptor; do not infer adult or non-adult status from I alone. |
| J — Juvenile | Juvenile plumage conventionally means the first true-feather plumage after down, often the plumage in which a young bird leaves the nest. It is a plumage stage, not a fixed calendar-year age; timing and appearance vary by species. | Use the source's Juvenile label. Do not assume every first-calendar-year bird remains juvenile, or that all juvenile birds map to EURING age 3. |
| S — SubAd | “Subadult” has been used inconsistently for different intermediate age or plumage classes, especially in raptor literature. | Treat as an observer-defined class with no universal calendar-year threshold. Do not map to a specific age without a species-specific rule. |
| Non-Juv | Literally “not juvenile”; this is not a standard age boundary. A bird can leave juvenile plumage during its first calendar year. | The exact Trektellen criterion is undocumented: do not infer age >1cy, adult status, or a particular plumage. |
| Non-adult | Broad general usage: not classed as adult, potentially including juvenile and later immature stages. “Immature” and “subadult” usage varies among authors and taxa. | Trektellen's exact inclusion rule is undocumented; retain separately and do not treat as identical to I or Non-Juv. |

These conventions are supported by the [BTO discussion of ageing terminology](https://www.bto.org/sites/default/files/field_craft_the_importance_of_age_in_bird_identification.pdf), which defines juvenile plumage and recommends calendar-year terminology when plumage terms are ambiguous; the [EURING Exchange Code 2020](https://euring.org/files/documents/E2020ExchangeCodeV202.pdf), which defines calendar-year age codes and states that age codes are based on plumage evidence; and Clark & Pyle's raptor-specific [recommendation on age-class plumage terminology](https://www.birdpop.org/docs/pubs/Clark_and_Pyle_2015_A_Recommendation_For_Standardized_Age-Class_Terms.pdf), which documents inconsistent uses of “subadult” and “immature.” Clark & Pyle's terminology paper concerns raptors, so its critique is evidence of ambiguity rather than a universal replacement vocabulary.

The same letter I in age and plumage is not the same attribute: age I is the combined >1cy (imm) / >1 an class, while plumage I means immature plumage. The fields are independent, so validation does not require them to match or exclude any combination. In the current released data, plumage I occurs in three distinct source observations, all with age 1 (two European Honey Buzzards and one Arctic Skua); there are no observations with both age I and plumage I. These co-occurrences are retained as recorded and are not treated as errors. A future code outside the schema enum fails output validation so its meaning and inclusion can be reviewed; it is not converted to missing or discarded.

## EURING comparison

EURING age codes are not the same as Trektellen age codes. EURING defines age from plumage evidence and uses its own code values; for example, EURING 3 means first-year, 5 means second-year, 7 means third-year and 9 means fourth-year. Its code A means after fourth-year, not adult. See the [EURING Exchange Code 2020](https://euring.org/files/documents/E2020ExchangeCodeV202.pdf), Age section (PDF pp. 13–14).

| Trektellen code and label | Closest EURING age code | Match and limitation |
| --- | --- | --- |
| A — Adult | 2, related only | EURING 2 means full-grown, age otherwise unknown; it is broader than Adult. EURING A means after fourth-year. |
| 1 — 1cy | 3, related only | Both refer to first calendar year; EURING 3 additionally specifies a full-grown bird. |
| 2 — 2cy | 5 | Same calendar-year age concept; code values differ. |
| 3 — 3cy | 7 | Same calendar-year age concept; code values differ. |
| 4 — 4cy | 9 | Same calendar-year age concept; code values differ. |
| I — >1cy (imm) | 4, related only | Both indicate older than first-year with no exact year; Trektellen uses different labels by language, and I alone does not establish maturity. EURING 4 is an age code. |
| J — Juvenile | None as an age code | EURING Plumage Code J means juvenile, but that is a different field; do not convert automatically to EURING age 3. |
| S — SubAd | None | EURING has no dedicated subadult age code; the calendar year cannot be inferred. |
| Non-Juv | None established | Literal label is not a EURING age class; Trektellen's precise criterion is unresolved. |
| Non-adult | None established | Broad general meaning is not a EURING age class; Trektellen's precise criterion is unresolved. |

The nearest-code column is a conceptual comparison, not an automatic conversion rule. Use the `euring_*` fields in [bird_attribute_codes.csv](bird_attribute_codes.csv) to inspect the match status and caveat for each value.

## Historical semantics and the explicit lookup

The active lookup is [historical_attributes.csv](../config/attributes/historical_attributes.csv). Its key is source_sheet + normalized descriptor; columns age/sex/plumage are independently assignable and note documents unresolved parts. Empty codes mean no supported conversion, not an assertion that the bird's class is biologically unknown.

The [Biolovision/ornitho FAQ](https://www.ornitho.ch/index.php?item=3&langu=en&m_id=36) specifies calendar-year ages and distinguishes adult, immature and female-type records. It describes immature plumage as after juvenile and before adult plumage. This does not by itself establish the >1cy bound shown for Trektellen I. It is relevant platform evidence, not proof that every Défilé observer used the labels identically.

| Historical description | Age | Sex | Conversion note |
| --- | --- | --- | --- |
| adulte / adultes | A | empty | Adult class. |
| 1ère année / 1ère année civile | 1 | empty | Calendar-year interpretation from Biolovision; same wording occurs in the digitised form details. |
| 2ème / 3ème / 4ème année | 2 / 3 / 4 | empty | Keep specific calendar-year information; do not reduce it to juvenile/immature. |
| mâle adulte / femelle adulte | A | M / F | Explicit joint description. Plural forms also listed in the lookup. |
| mâle / femelle | empty | M / F | Does not establish age. |
| type femelle | empty | FC | Does not establish female sex. |
| type femelle 1ère année civile | 1 | FC | Both attributes explicit. |
| immature / immatures | I | empty | Combined Trektellen class; original descriptor retained in remarks. |
| mâle immature / femelle immature | I | M / F | Same combined class; retain explicit sex and original descriptor. Plural forms also map. |
| type femelle immature | I | FC | Same combined class; retain original descriptor. Female type does not establish female sex. |
| > 1 an; mâle/femelle > 1 an | I | empty or M/F | Same Trektellen class as immature; original descriptor retained in remarks, adult status unspecified. |
| type femelle adulte / type femelles adultes | A | FC | Explicit adult age; female type does not establish female sex. |

### Combined historical age mapping (13 October 2026)

Historical `immature`/`immatures` and `> 1 an`, including sex-qualified and female-type forms, map to Trektellen age `I`. Trektellen displays this same class as `>1cy (imm)` in English and `>1 an` in French. This is a vocabulary harmonisation decision, not a claim that the original descriptions have identical biological meanings. Their original subgroup descriptors are retained in released remarks; source detail text and totals remain available in the ledger and component audit.

Organiser feedback supplied by the dataset maintainer on 13 October 2026 describes `>1 an` as birds that are not first-year and may be adults, particularly for kites and buzzards when an exact older age cannot be identified. The feedback provisionally suggests that local immature labels exclude first-year birds; Xavier's confirmation of that convention remains pending. This uncertainty does not prevent the agreed mapping to the combined Trektellen category.

The source workbook contains 269 records with immature descriptors, describing 613 birds. Five records explicitly separate immature and first-year groups in the same observation: four Marsh Harrier records (4 September 2012, 15 September 2017, 25 August 2020 and 15 September 2021) and one Great Cormorant record (1 September 2021). For example, `H-2017-2021-r65504` records `5x immatures / 1x 1ère année civile / 5x adultes`. These groups keep codes `I`, `1` and `A`, respectively; the immature wording remains attached only to its subgroup.

Do not automatically classify all age `I` birds as non-adults or adults. Analyses requiring the original distinction can use the preserved descriptors. Explicit first-year ages remain `1`; no plumage class is inferred from the combined age code.

No plumage value is extracted from a bird's age, taxon name or general prose. The dedicated historical descriptors currently provide no reviewed morph conversion. General comment/ remark fields are retained as observer text and are not scanned for speculative keywords.

## Conversion rules

Implemented in [attributes.py](../src/defile_dataset/attributes.py), called by the build:

1. Parse only the dedicated historical detail field. Components have the form `Nx description` and are separated by `/`. A bare `Nx` contributes an unspecified component.
2. Normalise Unicode, casing and spacing. Ignore only the explicitly documented trailing `(en vol)` annotation for attribute lookup; preserve the full original text. `(entendu)` carries hearing information rather than an age/sex/plumage class.
3. Look up each whole descriptor explicitly. Do not search for an adult/sex substring in arbitrary prose. Unknown and ambiguous expressions remain in the audit. Bare quantities, `(en vol)` and `(entendu)` do not require attribute review because they contain no age, sex or plumage information.
4. If subgroup quantities are smaller than the source count, add an undescribed remainder. If they exceed it, keep the unsplit source row and flag the conflict. Unparsed text also stays unsplit. Zero-quantity components do not create released rows.
5. Give each subgroup its own supported age, sex and plumage. Unknown descriptions and the remainder have missing attributes. Parsing and mapping are shared by the release and audit.
6. Retain source IDs in the source ledger. Internal normal subgroup IDs append `-part1`, `-part2`, etc., in source component order; released count IDs use the readable entry base, preserve the subgroup suffix and then append `-normal`. Reverse/local quantities are separate category rows, released once per original source entry. Fully converted descriptions are omitted from released remarks except age I descriptors, whose original wording is preserved to distinguish immature from > 1 an; unresolved wording and explicitly attributed daily context remain. Original text and subgroup lineage are preserved internally. Full lineage is in `interim/diagnostics/historical_components.csv`. Conservation checks sum released components back to their source and check expected IDs and collection dates.

Examples: `1x mâle adulte / 2x femelle adulte` with count=3 produces one adult male row with count=1 and one adult female row with count=2. `1x mâle adulte` with count=2 produces one adult male row and one undescribed row, each with count=1. `1x mâle > 1 an` gets sex=M and age=`I`, with `mâle > 1 an` retained in remarks and adult/immature status unspecified. No unsupported attribute classes are generated.

## Batumi correspondence is secondary

Table 3 of Wehrmann et al. (2019), printed p. 151 / PDF p. 17, was visually inspected in the stored paper (local evidence: `references/international/batumi-data-paper-2019.pdf`), [DOI](https://doi.org/10.3897/zookeys.836.29252).

| Trektellen | Batumi Table 3 | Match |
| --- | --- | --- |
| age A | ad | Matching adult concept. |
| age 1–4 | No dedicated calendar-year codes | Keep Trektellen specificity. First calendar year is not automatically equivalent to juvenile plumage. |
| age I | imm | Related only; Trektellen combines immature and >1 an labels, so neither maturity nor exact equivalence is established. |
| age J / Non-Juv | juv / nonjuv | J has a conventional juvenile-plumage meaning; Non-Juv is only a literal candidate correspondence because the native criterion is unknown. |
| age S / Non-adult | No dedicated equivalents | No forced conversion to imm. |
| sex M / F / FC | m / f / fc | Matching male, female and female-coloured/type concepts. |
| plumage D / L | dark / light | Matching dark/pale morph concepts. |
| Plumage W / I / B / E | No direct comparison established | Trektellen meanings are verified; no Batumi mapping is asserted. |
| Other native plumage codes | ful / mel / leu also occur in Batumi | No verified mapping yet. Do not guess. |

Do not create extra count rows or reduce native code specificity to imitate Batumi's schema.

## Audit and subgroup release

`interim/diagnostics/historical_attributes.csv` records each original detail and its mapping outcome. `historical_components.csv` records subgroup quantities, attributes, source IDs and released count IDs. The source ledger remains unsplit.

The 8 October 2026 build assesses 8,310 detail fields: 6,168 mapped, 584 partly mapped, and 1,558 unassigned. Recognised descriptions without attribute information are treated as mapped without assigning codes. Assumption notes keep immature mappings in the partly mapped review category even when all their age/sex codes have been assigned. All 672 previously unequal detail/count quantities are valid subsets, with no detail totals exceeding their source count. Splitting 1,264 retained source rows adds 1,675 released rows; main, reverse and local totals are unchanged for every source ID.

The 9 October 2026 parser update classifies the same 8,310 detail fields as 8,041 mapped and 269 partly mapped. Adult female-type descriptions map to age `A` and sex `FC`; bare quantities and flight/hearing annotations no longer require attribute review. The remaining partly mapped records carry the immature convention note.

The build records the crosswalk version separately from the subgroup splitting policy. Tests cover mixed sex/age, normal subsets, unknown labels, zero quantities, over-described counts, malformed detail, stable IDs, dates and source-total conservation.

On 13 October 2026 the maintainer accepted mapping both historical labels to I while retaining their original wording. These recognised descriptors no longer require a mapping review solely because they use different age labels. Earlier audit counts above describe the earlier policy. Remaining semantic work: obtain Xavier’s confirmation of whether historical immature consistently excludes first-year birds; this does not block the accepted combined mapping.

Residual remark prefixes `imm`, `imm.`, `im.`, `immature`, `> 1 an` and plural/case variants map to I when supported for the whole row; their original wording is retained even when age I is already present. Explicit conflicting age codes are retained with the original wording and a processing note. Uncertain expressions and quantities describing only a subset are not assigned to the whole row. The separate dataset extension `>1y` has been retired; both historical labels use the native code I.
