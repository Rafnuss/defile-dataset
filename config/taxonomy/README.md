# Historical taxonomy review

Open `historical_text_review.csv` first. It is the compact decision table: spelling and quantity variants are grouped, and long contextual narratives are in `historical_text_context.csv`. All CSV exports use UTF-8 with a BOM so Excel recognises French accents automatically.

## What to review

| Column | Meaning |
| --- | --- |
| `current_taxon` | Taxon currently used for these records. |
| `remark_examples` | Up to three original phrases; additional variants are counted. |
| `proposed_taxon` | Proposed taxon name and scientific concept, or an identification that still needs clarification. |
| `scope` | Entire count, or explicitly described birds within the source total. |
| `records` | Number of source-field occurrences in this group. |
| `birds` | Sum of the source counts, including any undescribed remainder. |
| `decision` | Your decision: `approve`, `reject`, `keep_current`, or `pending`. |
| `review_note` | Your correction, interpretation or reason. |
| `review_id` | Stable link to `review_group` in the detailed evidence file. |

Edit `decision` and `review_note`. If the proposed taxon is wrong, you can also edit `proposed_taxon` to give the name you intend; its precise checklist ID will be reconciled before application. These edits survive regeneration. Approval of a subset applies only to the explicitly described quantity; the remainder stays under its current identification. Unresolved alternatives are identification sets, not hybrid taxa or counts to divide between species.

`historical_text_evidence.csv` retains every original review entry, all spelling/quantity variants, dates, full text, source/released IDs, proposed checklist IDs and earlier review decisions. Match its `review_group` to the compact table's `review_id`. `historical_text_context.csv` contains uncertain identifications, companions, mixtures and rejected rarity identifications for separate reading; it requires individual interpretation. Editing the review does not itself change the dataset. `historical_text_mappings.csv` contains the compiled accepted rules used by the build.

The compact table keeps whole-count and subset cases separate. For example, `dont 10 Grive sp.` within 25 birds means 10 birds could move to Turdus sp., not all 25. `Avec 5 Pigeons colombins` describes companions and does not reidentify the counted pigeon. `merle sp` already maps to Turdus sp.; its verbal distinction remains in the evidence.

## Reproduce

After a dataset build, run from the repository root:

```sh
uv run python scripts/review/review_historical_taxonomy_text.py
```

Additional UTF-8 CSVs under `interim/diagnostics/taxonomy/` contain the complete original-text inventory, its summary and all historical source-name mappings. `historical-text-manifest.json` records input fingerprints and row counts. Original wording remains in the evidence; case, accents and whitespace are normalised only for matching. Published day-level annotations do not establish a record identification. Proposed IDs are checked against the pinned checklist.

Approved decisions are compiled with `uv run python scripts/review/resolve_historical_taxonomy_review.py`, then applied by the next dataset build. A review note containing an exact eBird code or scientific name overrides the proposed target; narrative notes remain notes. The build projects main-direction historical counts onto the accepted concepts, preserves the source ledger and creates explicit taxonomic subgroups where necessary. Independent age/time subgroups are not cross-assigned. The application audit is `output/audit/historical_taxonomy_review.csv`. Wording that expresses finer distinctions than an accepted broad concept remains in remarks.
