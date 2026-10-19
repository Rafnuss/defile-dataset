# Organiser feedback received 16 October 2026

Evidence: pasted replies from Benjamin Bruno and Xavier Birot-Colomb, retained verbatim in `raw/communications/` as private local research evidence. Xavier's reply has no sent timestamp in the pasted text. This review records raw-data decisions and preparation notes for a later manuscript update. No reply to the correspondents or manuscript edit is part of this review.

## Count and survey decisions

| Record | Evidence and decision |
| --- | --- |
| 26 August 2022, Trektellen 2263670 | Accept the recorded 06:50–21:30 local window: observer-attendance notes for Camille Schellenberger and Guillaume Hayart support the 21:30 finish. Benjamin cannot explain why counting finished so late. The reason is unexplained; the end time is accepted as supported by the notes. Retain counts and effort without shortening the session based on daylight. |
| Grive musicienne, 30 September and 2 October 2017 | Benjamin confirms exceptional passages of 7,915 and 8,222 birds after discussions involving Tilian and Rémi, who observed in 2017. Add a dated confirmation to the existing `remark` field on all 28 contributing historical rows. It confirms each day's total, not each entry separately. Counts and times stay unchanged. |
| Pinson des arbres, 3 October 2012 | Benjamin reports correcting Trektellen from 136,128 to half that value. Historical workbook `1966-2013`, row 24930, already contains 68,064. No further numerical correction is needed in the ingested historical source. |
| Pinson des arbres, 2012 report maximum | Benjamin flags an AI/OCR transcription error, separate from the 3 October count correction. Visual inspection of PDF p. 37 confirms the printed text « 1 ?23 795 ». The raw workbook count for 10 October is 123,795, corroborating the intended maximum. Correct the accepted report account and the stale report-derived workbook detail (`1966-2013`, F25426) to 123,795, with an explicit correction note. Both raw numeric counts (68,064 on 3 October and 123,795 on 10 October) remain unchanged. The attachment gives the malformed number 1,223,975, while the actual prior AI/OCR text had 1,223,795. The PDF stays unchanged. |
| Corbeau freux 1996 | Xavier supplies 17,783 birds from 30 September to 12 November, maximum 4,789 on 28 October. Preserve as correspondence evidence in this review, outside the dataset tables. Daily observations are incomplete. Do not add this total to the daily data or add the two existing entries (6 and 22) on top of it. |
| Pigeon colombin 1993 | Xavier supplies 7,690 birds from 17 September to 12 November, maximum 1,690 on 17 September. Preserve as correspondence evidence in this review, outside the dataset tables. This is evidence of passage in 1993, not a complete daily series. Keep 1994 as the current systematic daily-data start. |
| 30 August 2022 | Xavier recalls a day lost through an application/telephone problem and thought an empty form had been requested. Record missing count data, not no survey or zero birds. No effort window or count is reconstructed. |
| Full annual report 2022 | Xavier confirms he never finalised it. Status: non-existent as a completed report, rather than missing/search pending. An unfinished draft may exist. The preliminary LPO newsletter summary remains a separate source. |

These seasonal summaries are correspondence evidence only, retained in this review and the private original message. They are not new dataset resources, are not ingested by the build, and are not added to `count`, `survey` or the published-report annual-total ledger. The provisional `raw/reports/organiser-seasonal-summaries.csv` introduced in the earlier review was removed because it was outside the agreed data structure. The daily maxima are 4,789 rook on 28 October 1996 and 1,690 stock dove on 17 September 1993; these are subsets of the respective seasonal totals, not extra count rows. Any future representation of seasonal-only counts needs an explicit data-model decision.

Benjamin reports correcting the other queried timing cases in Trektellen. Exact revised endpoints were not supplied here; refresh and compare native exports before changing the corresponding local times. The possible duplicate on 19 November 2025 remains unresolved. Missing observation clocks on 15 July 2023 are not recovered. No new exclusion or estimated timing is introduced.

## Sampling and age information to use later

Xavier says immature normally means neither first calendar year nor adult. Benjamin says “>1 year” includes adults and is often the identifiable category for kites and buzzards. Keep these categories separate; this does not establish historical consistency for every observer.

Before 2008, Pierre Charvoz often recorded passerines and swallows using +, ++ and +++, without numeric counts. Historical paper forms were transcribed to Migraction from 2008 by Jean-Pierre Matérac, Michel Maire and Xavier; difficult handwriting and lost information limit completeness. From 2008, all-species counting was attempted, but a lone observer prioritised large birds. Benjamin identifies 2007 as the first chaffinch counting year, which is not evidence of systematic coverage of all passerines in 2007. Keep the existing 2008 systematic-count threshold and document observer-dependent coverage thereafter.

Xavier explicitly confirms that some entered counts are estimates: stock dove totals can be extrapolated from the composition of mixed pigeon flocks sampled in the morning; swallows and unidentified passerines can be counted for five minutes and extrapolated to an hour, repeated the following hour. This qualifies Benjamin's statement about “field counts”: recorded numbers may already incorporate field extrapolation. No estimate flags or precision are inferred for individual unmarked rows. The five-minute example need not apply in every era; published protocols describe other sampling durations.

Xavier's updated timeline: 1966–1992, Charvoz counted mainly pigeons during October holidays, with occasional other dates; 1993–2007, nearly daily volunteer attendance after retirement, often alone, with weekend support; 2008–2016, one salaried weekday observer and weekend volunteers, standard paper forms and evening Migraction entry by hour, not consistently; since 2017, two salaried observers with Swiss Ornithological Institute support and Sunday volunteers, live NaturaList entry followed by re-entered hourly Migraction summaries; live Trektellen entry from 2022. Earlier organiser notes mention Trektellen from 2021: keep this transition-date discrepancy visible instead of changing source-era IDs.

## Publication preparation retained for the next step

Xavier agrees to participate in a data paper and expresses trust in the proposed Zenodo/GBIF publishing route with Vogelwarte as publisher. This is not a new explicit confirmation of CC BY licensing or permission to publish personal observer names or copyrighted report extracts.

His suggested author sequence is Raphaël first, then Benjamin Bruno (volunteer observer and historical-data checking), Jean-Pierre Matérac and Michel Maire (volunteer observers and historical digitisation), Pierre Charvoz (volunteer observer through 2007 and founder of the long record), and Xavier Birot-Colomb (salaried observer, historical digitisation and coordination jointly with Benjamin). Treat this as a proposal, not an agreed author list. He reports no ORCID for these collaborators and LPO affiliation except Charvoz, associated with Nos Oiseaux. Exact affiliations, contributions and author agreement remain to be established.

Acknowledgements suggested: all volunteers and salaried observers, especially Robert, Lutz, Roger, Isabelle, Stéphane, Ted Green, Hilde and Jost. Funders named: Station Ornithologique Suisse, Région Auvergne-Rhône-Alpes, GOBG, Syndicat Intercommunal du Vuache and Fondation Hans Wildorf (spelling as supplied; verify official names later). Do not infer full names or specific grant periods.

Weather-source questions, rainfall timing, forecast requests and dissemination questions are outside this raw-data edit. The manuscript will be updated only after further instructions.

## Verification follow-up

The first review checked the numeric 3 October correction but missed the stale malformed maximum in the workbook detail consumed by Explore. The follow-up corrects that source annotation and replaces the earlier unresolved wording with the corroborated 123,795. Explore’s generated `records.top_days` still contained the old note when inspected; it must be regenerated from the corrected dataset before the website displays the correction. No authored Explore accounts were edited.
