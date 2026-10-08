# Accepted report tables

These supporting inputs were reviewed and accepted on 7 October 2026. The count/survey build reads them directly; PDF extraction and curation are not part of it.

| File | Contents |
| --- | --- |
| `report_text.csv` | Accepted French prose: year, category, key and text; 779 populated accounts from 21 available annual reports. |
| `annual-totals.csv` | Published main-direction counts transcribed by year/species; gaps remain unknown, not zero. |
| `annual-total-pages.csv` | PDF page numbers for totals matched unambiguously by year, species and count to the archived extraction ledger. Missing page references open the report at its beginning. |
| `observation-interruptions.csv` | Report statements about closures, partial coverage and weather impacts, with evidence and source pages. |

The text was extracted and edited with AI assistance. Tables, charts and some other material are omitted, so it is not a complete transcription. Shared passages are not independent evidence. Missing species accounts do not establish absence. The full 2022 report is unavailable; current prose covers available reports from 2004 through 2025.

The build copies accepted report prose to the release and checks columns, unique keys, category/key combinations and taxon links against `config/schema/datapackage.json`. It does not rebuild text or require extraction hashes and page-review records. Edit the accepted CSV when adding or correcting report text, then rebuild the dataset.

Annual totals guide audit comparisons without overwriting recorded counts. Transcribed species totals retain published values even where printed subtotals disagree. Missing, unreadable, unverified OCR, separately reported reverse counts and published bounds are not invented as main-direction counts. See `taxonomy/report_taxa.csv` for mappings.

Interruption statements are evidence, not an automatically reconstructed attendance calendar. Maintained historical decisions live in the workbook; Trektellen decisions in `config/survey-status/`. Audit windows and review notes live in `config/audit-settings/`.

Original documents and their inventory remain in references/ (local evidence: `references/README.md`). Raw extraction, processed text, source-label distinctions, curation records and scripts are retained in the report-processing archive (local evidence: `archive/report-processing/README.md`).
