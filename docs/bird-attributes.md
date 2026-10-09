# Age, sex and plumage: historical data to Trektellen

First implementation, 7 October 2026. Trektellen is the target vocabulary because it is the ongoing collection system. Batumi Table 3 provides a secondary comparison, not a replacement vocabulary. Historical counts are split into their described subgroups and an undescribed remainder. The source total is preserved; no attributes are inferred for the remainder.

## Where the information lives

| Recording era | Received field | Evidence and limits |
| --- | --- | --- |
| Notebook/digitised daily data, 1966–2013 | detail: 1,121 recovered rows, from 2001 onward | Imported once from Alldata into count_2021.xlsx using unique species/date/count matches. Corrected reference times retained. Marginal counts/proportions are derived summaries, not extra observations. |
| Spreadsheet/forms, 2014–2016 | detail: 550 non-empty rows | Structured quantity/description text, often several components per count. No separate historical plumage column. |
| NaturaList/transition, 2017–2021 | details: 6,639 non-empty rows | Similar quantity/description text. Entry clocks are separate from bird attributes. The received sheet includes a transition to Trektellen in 2021, so its label does not prove every record's original platform. |
| Trektellen exports, 2022–2026 | age, sex, plumage | Native structured fields: 12,498 age entries, 3,991 sex entries and 141 plumage entries in the inspected snapshots. Values are preserved; native spellings are not silently normalised. |

The original historical exports (`data_brute_DE_2014_2021.xlsx`, `data_défilé_2016.xlsx`, `data_défilé_2020.xlsx`) retain Détails text rather than separate age/sex/plumage fields. The one-off import log (local evidence: `docs/imports/alldata-2026-10-07/README.md`) documents the earlier recovery. The historical build now reads only count_2021.xlsx; archived workbooks are not dependencies. The published four-table schema omits historical_in_list and trektellen_group_id as requested; the originals remain archived.

## Trektellen target dictionary and evidence

The authoritative code definitions and enum constraints are in [config/schema/datapackage.json](../config/schema/datapackage.json). The evidence dictionary [bird_attribute_codes.csv](bird_attribute_codes.csv) is generated from it. It records the native code, meaning, evidence status, example native data ID, evidence URL and the Batumi comparison. This is an inventory of codes observed in our files, not a claim that the entire Trektellen vocabulary has been recovered.

Code meanings were checked against public English count tooltips and matched to the native export by site/date, species, minute and numerical direction/local component where available. Examples include the [1 October 2026 count](https://www.trektellen.org/count/view/2422/20261001?language=english), [30 July subadult](https://www.trektellen.org/count/view/2422/20260730?language=english), [19 September dark morph](https://www.trektellen.org/count/view/2422/20260919?language=english) and [27 September pale morph](https://www.trektellen.org/count/view/2422/20260927?language=english). The public label and original native code are separate pieces of evidence.

| Attribute | Native code | Established meaning | Treatment |
| --- | --- | --- | --- |
| Age | A | Adult | Historical adult expressions can map directly. |
| Age | 1, 2 | First, second calendar year (1cy/2cy) | Map explicit historical calendar-year expressions. |
| Age | 3, 4 | Numeric calendar-year continuation | Observed native codes; the meaning follows the verified 1/2 convention, rather than a recovered full code dictionary. Historical explicit third/fourth-year expressions use these codes. |
| Age | I | >1cy (imm) in the public UI | Historical immature labels map to I under the documented local-usage assumption below; other non-adult or unspecified older labels are not automatically equivalent. |
| Age | S | SubAd | Confirmed public display; no matching historical phrase yet. |
| Age | J | Provisional juvenile | Native value observed, but no code-to-label confirmation recovered. Preserve it; no historical J conversion yet. |
| Age | Non-Juv | Public label Non-Juv | Exact definition still needs clarification; do not automatically equate calendar age >1 with a plumage class. |
| Age | Non-adult, non_adult | Definition/alias relationship pending | Both spellings occur. Preserve each native value for now. The checked recent page did not display the attribute for Non-adult. |
| Sex | M, F | Male, female | Historical unambiguous expressions map directly. |
| Sex | FC | Female type | Includes birds not positively sexed female. Map type femelle to FC, never F. |
| Plumage | D, L | Dark morph, pale morph | Confirmed public display; no explicit historical morph descriptor found in the current dedicated detail fields. |
| Plumage | W, I, B, E | Not verified | Preserve native codes; do not infer their meanings from the letters. |

The same letter I in age and plumage is not the same attribute. Codes must always be interpreted with their column. The reviewed native values remain unchanged. A future code outside the schema enum fails output validation so its meaning and inclusion can be reviewed; it is not converted to missing or discarded.

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
| immature / immatures | I | empty | Assumed local older non-adult class; organiser confirmation pending. |
| mâle immature / femelle immature | I | M / F | Same age assumption; retain explicit sex. Plural forms also map. |
| type femelle immature | I | FC | Same age assumption; female type does not establish female sex. |
| > 1 an; mâle/femelle > 1 an | >1y | empty or M/F | Literal lower bound in years; adult status unspecified. Dataset extension, excluded from adult/non-adult proportions. |
| type femelle adulte / type femelles adultes | A | FC | Explicit adult age; female type does not establish female sex. |

### Assumption for historical immature labels (8 October 2026)

Historical `immature`/`immatures`, including sex-qualified and female-type forms, are mapped to age `I` in all three historical sheets. We assume Défilé observers used these labels for non-adults older than the first calendar year, separately from `1ère année`. This is an accepted harmonisation assumption based on local usage, not a verified Biolovision-to-Trektellen equivalence. It applies across species and years, including those without direct evidence of the distinction. Confirmation from the organisers by email remains pending; no confirmation has yet been requested.

The source workbook contains 269 records with immature descriptors, describing 613 birds. Five records explicitly separate immature and first-year groups in the same observation: four Marsh Harrier records (4 September 2012, 15 September 2017, 25 August 2020 and 15 September 2021) and one Great Cormorant record (1 September 2021). For example, `H-2017-2021-r65504` records `5x immatures / 1x 1ère année civile / 5x adultes`. The Short-toed Eagle record `H-2017-2021-r65119` (25 August 2021) has detail `1x immature` and remark `2A ou 3A en migration active.` The 2006 Golden Eagle report (local evidence: `archive/report-processing/text/normalized/2006/avibase-5F8E7CA8.txt`) describes immatures aged 3–4 years. These support the local interpretation without proving that every observer used it consistently.

Platform terminology remains broader: the [French Biolovision FAQ](https://wiki.biolovision.net/FAQ_utilisateurs) defines immature from signs of immature plumage when exact age is unknown, without a calendar-year minimum. [Ornitho guidance from June 2024](https://www.ornitho.ch/index.php?a=995&langu=en&m_id=1164) also discusses immature among labels used for birds born that year. Trektellen's `I` displays as `>1cy (imm)` in English and `>1 an` in French. The autumn observation window does not itself establish hatch year. If local immature labels included first-year birds, this mapping would overstate their calendar age.

Each mapped descriptor carries an assumption note into the processing audit and remarks, so these assignments remain identifiable for later review. Explicit first-year ages remain `1`; mixed groups retain their separate subgroup ages. Original detail text and source totals are preserved. The separate `> 1 an` descriptors map literally to `>1y`; they do not establish adult or immature status.

No plumage value is extracted from a bird's age, taxon name or general prose. The dedicated historical descriptors currently provide no reviewed morph conversion. General comment/ remark fields are retained as observer text and are not scanned for speculative keywords.

## Conversion rules

Implemented in [attributes.py](../src/defile_dataset/attributes.py), called by the build:

1. Parse only the dedicated historical detail field. Components have the form `Nx description` and are separated by `/`. A bare `Nx` contributes an unspecified component.
2. Normalise Unicode, casing and spacing. Ignore only the explicitly documented trailing `(en vol)` annotation for attribute lookup; preserve the full original text. `(entendu)` carries hearing information rather than an age/sex/plumage class.
3. Look up each whole descriptor explicitly. Do not search for an adult/sex substring in arbitrary prose. Unknown and ambiguous expressions remain in the audit. Bare quantities, `(en vol)` and `(entendu)` do not require attribute review because they contain no age, sex or plumage information.
4. If subgroup quantities are smaller than the source count, add an undescribed remainder. If they exceed it, keep the unsplit source row and flag the conflict. Unparsed text also stays unsplit. Zero-quantity components do not create released rows.
5. Give each subgroup its own supported age, sex and plumage. Unknown descriptions and the remainder have missing attributes. Parsing and mapping are shared by the release and audit.
6. Retain source IDs in the source ledger. Internal normal subgroup IDs append `-part1`, `-part2`, etc., in source component order; released count IDs use the readable entry base, preserve the subgroup suffix and then append `-normal`. Reverse/local quantities are separate category rows, released once per original source entry. `source_count_id` retains the original ID. Fully converted descriptions are omitted from released remarks; unresolved wording and explicitly attributed daily context remain. Original text and subgroup lineage are preserved internally. Full lineage is in `interim/diagnostics/historical_components.csv`. Conservation checks sum released components back to their source and check expected IDs and collection dates.

Examples: `1x mâle adulte / 2x femelle adulte` with count=3 produces one adult male row with count=1 and one adult female row with count=2. `1x mâle adulte` with count=2 produces one adult male row and one undescribed row, each with count=1. `1x mâle > 1 an` gets sex=M and age=`>1y`, leaving adult/immature status unspecified. No unsupported attribute classes are generated.

## Batumi correspondence is secondary

Table 3 of Wehrmann et al. (2019), printed p. 151 / PDF p. 17, was visually inspected in the stored paper (local evidence: `references/international/batumi-data-paper-2019.pdf`), [DOI](https://doi.org/10.3897/zookeys.836.29252).

| Trektellen | Batumi Table 3 | Match |
| --- | --- | --- |
| age A | ad | Matching adult concept. |
| age 1–4 | No dedicated calendar-year codes | Keep Trektellen specificity. First calendar year is not automatically equivalent to juvenile plumage. |
| age I | imm | Related; Table 3 gives no explicit calendar-year bound, so do not assert exact equality from the paper alone. |
| age J / Non-Juv | juv / nonjuv | Candidate correspondences; exact native definitions remain to be checked. |
| age S / Non-adult | No dedicated equivalents | No forced conversion to imm. |
| sex M / F / FC | m / f / fc | Matching male, female and female-coloured/type concepts. |
| plumage D / L | dark / light | Matching dark/pale morph concepts. |
| Other native plumage codes | ful / mel / leu also occur in Batumi | No verified mapping yet. Do not guess. |

Do not create extra count rows or reduce native code specificity to imitate Batumi's schema.

## Audit and subgroup release

`interim/diagnostics/historical_attributes.csv` records each original detail and its mapping outcome. `historical_components.csv` records subgroup quantities, attributes, source IDs and released count IDs. The source ledger remains unsplit.

The 8 October 2026 build assesses 8,310 detail fields: 6,168 mapped, 584 partly mapped, and 1,558 unassigned. Recognised descriptions without attribute information are treated as mapped without assigning codes. Assumption notes keep immature mappings in the partly mapped review category even when all their age/sex codes have been assigned. All 672 previously unequal detail/count quantities are valid subsets, with no detail totals exceeding their source count. Splitting 1,264 retained source rows adds 1,675 released rows; main, reverse and local totals are unchanged for every source ID.

The 9 October 2026 parser update classifies the same 8,310 detail fields as 8,041 mapped and 269 partly mapped. Adult female-type descriptions map to age `A` and sex `FC`; bare quantities and flight/hearing annotations no longer require attribute review. The remaining partly mapped records carry the immature convention note.

The build records the crosswalk version separately from the subgroup splitting policy. Tests cover mixed sex/age, normal subsets, unknown labels, zero quantities, over-described counts, malformed detail, stable IDs, dates and source-total conservation.

Remaining work: confirm the accepted immature mapping assumption with the organisers by email, confirm the interpretation of older-than-one-year descriptors and unverified native codes. Original descriptions remain available for review.

Residual remark prefixes `imm`, `imm.`, `im.`, `immature` and plural/case variants are removed when age I is assigned or already present. Explicit conflicting age codes are retained with the original wording and a processing note. Uncertain expressions and quantities describing only a subset are not assigned to the whole row. The historical local-usage assumption for immature remains explicit. `>1y` is a literal age lower bound, not a native Trektellen code or a replacement for I.
