# Manuscript content review against Xavier’s reply

Reviewed on 16 October 2026: supplied PDF `32575 (1).pdf`, titled *Six decades of visible bird migration counts at Défilé de l’Écluse, France, with documented survey effort* (15 pages), against Xavier Birot-Colomb’s reply received on 16 October 2026 and the current dataset documentation. Page references below refer to that supplied PDF. This is a content review and suggested wording, not an edit to the manuscript. Authorship, funding, acknowledgements and publication permissions are outside scope.

## Main assessment

The manuscript already describes the heterogeneous recording history and warns against direct comparisons. Xavier’s reply strengthens that account; it does not require a different overall framing. The substantive additions concern how estimates enter the recorded counts, the limited meaning of passerine start years, and the distinction between original field records and the digital compilation that survives. These belong mainly in Sampling methods, with short qualifications under Taxonomic coverage and Traits coverage.

## Changes supported by the reply

| Location | Finding | Recommended change |
| --- | --- | --- |
| p. 3, Project description / Personnel | “From 2008 to 2017, one salaried observer” overlaps the next sentence and disagrees with Xavier and the methods/figure. | Change the period to 2008–2016. Describe one weekday salaried observer with weekend volunteer coverage, followed by two salaried observers from 2017 with Sunday volunteers. This is survey-method history, independent of the author list. |
| pp. 3–4, monitoring history | “Intermittent counts” is correct but does not explain the early sampling concentration. | Add that the pre-1993 record predominantly reflects October pigeon counts during Charvoz’s holidays, with occasional dates outside October. Do not imply equal taxonomic or seasonal coverage across the six decades. Fig. 2 already conveys October pigeon passage; the prose can match it. |
| p. 4, species scope | General observer-dependence is already acknowledged, but the loss of numerical passerine information is understated. | Explain that Charvoz often recorded passerines and swallows as +, ++ or +++ rather than numerical counts before 2008. These cannot be converted into numerical totals. Efforts to quantify all species increased from 2008, but lone observers continued to prioritise large birds. |
| p. 4, counting and estimation | The text discusses estimated flock sizes and variable swallow protocols, but not the two distinct extrapolations Xavier describes. | Add stock dove daily extrapolation from sampled mixed-pigeon flock composition and five-minute swallow/unidentified-passerine counts extrapolated to hourly passage, repeated in subsequent hours. These are examples, not a uniform historical protocol. Include swifts among groups for which Xavier reports frequent estimation, without assigning them the specific five-minute procedure. |
| p. 4, recording history | “Later transcribed into the LPO database” is vague. | Identify retrospective digitisation to Migraction beginning in 2008. Mention possible transcription loss and non-numerical source notes without implying that every original field record survived. Keep the existing distinction between hourly field forms and the predominantly daily digital compilation through 2013. |
| p. 4, NaturaList | Live timestamps are described, but the parallel workflow is missing. | Add that live NaturaList recording from 2017 was followed by hourly summaries re-entered into Migraction. Distinguish that historical banking step from the original live records retained in the received compilation. Do not imply that all released records were reduced to hourly summaries. |
| p. 6, systematic start years | The existing analytical-convention caveat is useful but could still imply complete enumeration after a threshold. | Explicitly state that a start year does not guarantee exhaustive recording of the taxon thereafter. The 2008 passerine threshold marks increased quantification, not consistently complete coverage. Benjamin’s first chaffinch counts in 2007 do not establish systematic coverage of every passerine in 2007. |
| p. 7, age definitions | Broad class caveats are present but the local immature versus >1 year distinction is absent. | Explain that Xavier normally uses immature for birds neither first-calendar-year nor adult; >1 year can include adults. The release currently maps both historical labels to native Trektellen age I and preserves their original descriptors in remarks. Do not describe I as a pure biologically immature class, or claim the two historical descriptors have identical meanings. |
| pp. 4–6, limitations and missing records | Generic gaps are described, but technical loss and seasonal-only survival are not explicit. | Add a brief distinction between lack of observation, loss of recorded data, qualitative recording and surviving seasonal syntheses. Rook 1996 and stock dove 1993 are examples of seasonal evidence without a complete daily series. Their totals are outside the count tables. Xavier recalls a technical loss on 30 August 2022: absence of a record does not establish no survey or zero passage. |

The estimation paragraph should also make clear that a blank `count_estimation` field means no explicit qualifier was recorded, not that the number is necessarily an exhaustive count. That meaning is already correct in the column dictionary; no schema change or retrospective flagging of unmarked rows is warranted.

## Points to resolve or qualify

**Trektellen adoption, p. 4 and Fig. 2:** the manuscript and figure state introduction in 2021. Xavier’s latest reply says direct entry from 2022, while earlier organiser information and the archived 2021 export support some 2021 use. These may describe a transition rather than a contradiction, but the exact interpretation is not established. Use “Native Trektellen exports are used from 2022 onward” for the dataset boundary. Avoid asserting a single universal adoption date until the 2021 transition is clarified. The 2017–2021 worksheet remains a received-file boundary, not proof of a single platform throughout that period.

**Age consistency:** Xavier says “normally”; this supports the intended local convention, not a retrospective guarantee for all observers and years. It is sufficient to update the pending-feedback wording in the documentation, while retaining the historical-consistency limitation and the accepted mapping.

**Survey versus species completeness:** effort and `survey_complete` do not establish complete enumeration of every taxon. Observer-dependent omissions and extrapolation remain relevant within attended intervals. A sentence distinguishing interval status from taxon-specific counting scope would prevent an overly strong reading of the otherwise appropriate effort description.

**2022 report:** no completed annual report exists; it was never finalised. The current paper does not call it a missing report, so a new paragraph is unnecessary. Any source inventory or supplementary description should use “never finalised” rather than “not located”; the preliminary newsletter remains a separate source.

## Suggested wording for the main additions

### Sampling methods: scope and estimates

“Before 2008, passerines and swallows were often recorded qualitatively using +, ++ and +++ rather than numerical counts. Attempts to quantify all species increased from 2008, but coverage remained dependent on observer availability and passage intensity, with lone observers prioritising large birds. The adopted start years therefore do not guarantee exhaustive recording of every taxon thereafter.”

“Recorded quantities include field estimates and extrapolations. Stock Dove totals could be extrapolated from the proportion identified within sampled mixed pigeon flocks. For swallows and unidentified passerines, five-minute counts could be extrapolated to hourly passage and repeated in subsequent hours. These practices were not documented uniformly across years or records; the absence of an explicit estimation qualifier does not establish that a numerical count was exhaustive.”

### Recording history

“Historical paper records were retrospectively digitised into Migraction from 2008. Standardised paper forms were subsequently entered in the evening, often as hourly summaries, although this resolution did not survive consistently in the received compilation. From 2017, salaried observers recorded birds directly in NaturaList, with hourly summaries also re-entered into Migraction. The compilation retains original timestamps where available; native Trektellen exports are used from 2022 onward.”

### Traits coverage

“In local observer terminology, ‘immature’ normally excluded both first-calendar-year birds and adults, whereas ‘>1 year’ could include adults. Both historical descriptors are mapped to Trektellen age I in the released data, with the original wording retained in remarks. This shared code should not be interpreted as evidence of identical maturity status.”

### Missing-data interpretation

“Missing numerical records can reflect unmonitored periods, qualitative recording, technical data loss or incomplete digitisation. In some species-years, only a seasonal synthesis survives; such totals cannot reconstruct a daily series and have not been added to the released count table.”

## Other content issues visible in this PDF

- The abstract (p. 1) and Temporal coverage (p. 7) end the dataset on 1 October 2026. The current release extends to 15 October 2026. Choose one release snapshot and align both statements, Fig. 2 and the supplementary summaries with it. The local figure-input manifest currently ends on 12 October, so the prose and figure inputs already refer to different snapshots. Recalculate the reported coverage medians when regenerating the figure rather than assuming they are unchanged.
- The nocturnal-acoustic paragraph on p. 5 contains unresolved factual placeholders for year, equipment, position, schedule and archive. Xavier’s reply does not supply these. Remove the detailed paragraph until those facts are documented, or reduce it to a supported statement about exclusion from the present dataset; retain the existing limitation that these counts principally cover visible diurnal passage.
- The three main scientific tables can remain the focus. The repository also distributes curated report and paper accounts, so distinguish the three core observation resources from any accompanying text resources when finalising the Data resources description. The seasonal-only correspondence evidence is not another released resource.

## Documentation alignment to make alongside manuscript edits

- `docs/sampling-history.md` already records Xavier’s timeline, qualitative observations and estimation examples. Preserve its distinction between published protocols, organiser recollections and received-file resolution.
- `docs/bird-attributes.md` still says Xavier’s confirmation is pending in two places. Replace this with the newly received “normally neither first-calendar-year nor adult” clarification, retaining uncertainty about universal historical consistency. Do not alter the accepted combined age-I mapping merely to reflect the new prose.
- `docs/organiser-feedback-2026-10-16.md` says “Keep these categories separate”. Clarify that their original descriptors remain distinguishable in remarks while their released age code is shared; otherwise the review contradicts the implemented mapping.
- The treatment of the late 26 August 2022 finish, confirmed song-thrush passages and the corrected chaffinch transcription is appropriately record-level evidence. These need not be added as anecdotes to the manuscript; the general quality-control description already provides a suitable place for their role.

The manuscript PDF and scientific inputs were not changed by this review.
