# Release and publication

The publication proposal uses GitHub for code and maintained documentation, Zenodo for a frozen complete research release, GBIF for biodiversity discovery, and a data paper for reviewed methods and contributor recognition. These products should identify and link the same release. The planned licence is CC BY 4.0 for first-party structured observation data and its associated metadata/documentation, and CC BY 4.0 is requested for the data paper. The rights holder, contributor attribution and permissions must be confirmed before public release; current generated output is not a citable frozen release.

## Prepare a release

1. Review scientific audit findings and document unresolved limitations, source selection and provisional seasons.
2. Freeze the five research CSVs, descriptor, usage guide, column/attribute dictionaries, provenance hashes and relevant audit evidence together. The package licence applies to the first-party structured observation resources (`count`, `survey`, `taxonomy`) and original documentation. `report_text` and `paper_text` are curated extracts from third-party works and are excluded from the CC BY grant unless rights-holder permission is obtained; mark this exception clearly in the archive. Include generated files explicitly: a code-only archive omits ignored outputs.
3. Generate GBIF Event/Occurrence CSVs from those exact tables. Use CC BY 4.0 for the GBIF export, subject to rights-holder confirmation; record the same machine-readable licence in IPT/EML. Agree persistent exported IDs, geography, publisher/IPT and public attribution; complete EML and validate interpreted timing, taxonomy, zero/presence and direction categories. See [the GBIF guide](gbif.md).
4. Deposit the reviewed research product with a version-specific DOI and publish the agreed GBIF representation. Verify downloads, citations and links between products.
5. Pin forecast/visualisation consumers and paper statistics to the frozen release. Publish future seasons as new versions, clearly marking unfinished seasons provisional.

Detailed weather, narratives, native IDs, processing notes, crosswalks and report text remain in the research product even when omitted from GBIF. The `report_text` and `paper_text` extracts remain outside the CC BY grant until rights are cleared. Software code has no licence declared by this data licence; choose and apply a separate software licence before treating the code repository as an openly licensed code release. Observer attribution and free text require the agreed public-field policy.

## Paper and coordination

The manuscript belongs in paper/ (local evidence: `paper/manuscript.qmd`), with figures and summaries generated from the cited release. The recorded proposal is Biodiversity Data Journal; journal fit, fees, funding and authorship remain decisions for the team. Journal and precedent research (local evidence: `paper/research/publication.md`) is separate from maintained dataset methods. The organiser email draft (local evidence: `paper/coordination/email-organisateurs.md`) gathers permissions, credit and scientific clarifications; it is not a sent message or a decision record.

## Outstanding work

GitHub issues own progress: [source reconciliation](https://github.com/Rafnuss/defile-dataset/issues/2), [GBIF validation](https://github.com/Rafnuss/defile-dataset/issues/5), [release](https://github.com/Rafnuss/defile-dataset/issues/6), [paper](https://github.com/Rafnuss/defile-dataset/issues/7) and [Explore](https://github.com/Rafnuss/defile-dataset/issues/8). Dated reviews preserve evidence rather than a second live checklist.

The 1996 Part I review (local evidence: `docs/reviews/1996-paper/README.md`) retains published 1993 reference totals, dated observer gaps and the fixed GMT+1 convention. Reconcile those against the original records and season before changing counts or timing. Part II has been recovered. Xavier Birot-Colomb confirms that the 2022 annual report was never finalised (reply received 16 October 2026); no completed report is awaiting recovery. Remote preservation status belongs in the reference/evidence inventory. See [the dated organiser feedback](organiser-feedback-2026-10-16.md) for authorship, acknowledgements, funding and protocol information retained for the next manuscript update.

Source cleaning, scientific decisions and publication exports belong in this repository; forecast modelling belongs in defile-migration-forecast and presentation in defileViz. The dashboard planning draft (local evidence: `paper/planning/dashboard-design.md`) is retained for transfer when that implementation resumes.
