# Accepted report tables

The annual-report inputs were reviewed and accepted on 7 October 2026; the four Nos Oiseaux paper extracts were added on 8 October 2026. The count/survey build reads them directly; PDF extraction and curation are not part of it.

| File | Contents |
| --- | --- |
| `report_text.csv` | Accepted French prose: year, category, key and text; 781 populated accounts from 21 available annual reports. |
| `paper_text.csv` | French species accounts from all four Nos Oiseaux papers: source_id, category, key and text; 100 populated accounts. |
| `annual-totals.csv` | Published main-direction counts transcribed by year/species; gaps remain unknown, not zero. |
| `annual-total-pages.csv` | PDF page numbers for totals matched unambiguously by year, species and count to the archived extraction ledger. Missing page references open the report at its beginning. |
| `observation-interruptions.csv` | Report statements about closures, partial coverage and weather impacts, with evidence and source pages. |

The text was extracted and edited with AI assistance. Tables, charts and some other material are omitted, so it is not a complete transcription. Shared passages are not independent evidence. Missing species accounts do not establish absence. The full 2022 report is unavailable; annual-report prose covers available reports from 2004 through 2025.

Misplaced species passages were corrected on 9 October 2026 after screening both accepted prose files (local evidence: `docs/imports/species-account-corrections-2026-10-09/README.md`, with the moves, exact before/after values and preservation checks).

The build copies both accepted prose CSVs unchanged into the release and records their input/output checksums. It checks columns, unique keys, category/key combinations and annual-report taxon links against `config/schema/datapackage.json`. It does not rebuild text or require extraction hashes and page-review records. Edit the accepted CSV when adding or correcting report text, then rebuild the dataset.

Annual totals guide audit comparisons without overwriting recorded counts. Transcribed species totals retain published values even where printed subtotals disagree. Missing, unreadable, unverified OCR, separately reported reverse counts and published bounds are not invented as main-direction counts. See `taxonomy/report_taxa.csv` for mappings.

Interruption statements are evidence, not an automatically reconstructed attendance calendar. Maintained historical decisions live in the workbook; Trektellen decisions in `config/survey-status/`. Audit windows and review notes live in `config/audit-settings/`.

Original documents and their inventory remain in references/ (local evidence: `references/README.md`). Raw extraction, processed text, source-label distinctions, curation records and scripts are retained in the report-processing archive (local evidence: `archive/report-processing/README.md`).

## Paper text

`paper_text.csv` follows the same lean category/key/text format as annual report text. Its primary key is `(source_id, category, key)`: a source ID replaces the annual report year because the papers include two parts published in 1996 and two multi-year syntheses. `defile-paper-1996-I` and `defile-paper-1996-II` describe 1993; `defile-paper-2019` covers 1993–2017; `defile-paper-2020` covers 1993–2019. All accounts are category `species`.

Species keys follow the existing Avibase mappings. Three shared passages retain `group-corbeau-freux-choucas-des-tours`, `group-hirondelles-rustique-fenetre-rivage` and `group-aigle-pomarin-criard`; shared totals are not allocated to individual species. Paper taxa need not occur in the recorded count taxonomy. The schema enumerates the accepted paper keys and validates source IDs and unique accounts.

Counts by paper are 24, 34, 25 and 17 respectively. The French text retains paragraph breaks, published summary statistics, citations and discrepancies. Figures and tables are omitted. Notes in 1996 Part II concern species not systematically counted; 2020 forest-species recording was irregular before 2008 and observer-dependent. Historical taxon labels, page references, OCR corrections and readable extracts are retained in the paper extraction archive (local evidence: `archive/report-processing/papers/README.md`). The accepted CSV is maintained directly; extraction code is not part of the build.
