# Taxonomy and source mappings

The released tables contain birds only. `taxon_id` is the Avibase concept ID; `trektellen_species_id` is an optional comma-separated list of distinct native IDs. `source_taxa` preserves the source-label crosswalk as JSON. Internal `kind` remains in the audit/source mapping for filtering, but is absent from released taxonomy.csv.

The pinned AviList **v2025 extended checklist** supplies released names, ranks and higher taxonomy first; eBird/Clements **2025 integrated checklist** fills missing concepts or fields and supplies eBird codes. It does not supply French common names. Historical French names below are actual source names, not translated eBird names. Trektellen English names come from the mapping and are checked against observed export labels in taxonomy-review.csv (local evidence: `interim/diagnostics/taxonomy/taxonomy-review.csv`). No French equivalents or alternative taxon IDs have been invented. The CSV includes all source rows for these cases, even source labels with no observations in the current export.

## Corrections implemented

| Source | Native ID | Released eBird concept | Reason |
| --- | --- | --- | --- |
| Species unidentified | 480 | bird sp.; Aves sp.; bird1; avibase-AF0D818A | An unidentified bird is not a no-species entry. Four entries include 7 main-direction birds and 4 local birds. |
| Whitethroat | 348 | Greater Whitethroat (AviList display: Common Whitethroat); Curruca communis; grewhi1; avibase-14AFBA82 | Previously merged incorrectly with Lesser Whitethroat (347, Curruca curruca). Separate source names support separate species. |
| Laridae sp. | 690 | gull/tern sp.; Laridae sp.; y00728; avibase-1B8C48CC | Previously mapped to Larus sp., a narrower genus. The checklist scientific name now matches the source family label. |

## Species limits confirmed by the dataset owner

The following source scopes were explicitly confirmed on 7 October 2026. These corrections replace legacy combined concepts with the corresponding AviList species; they do not infer identifications solely from the site's geographic location.

| Source labels | Previous combined concept | Corrected species and Avibase ID |
| --- | --- | --- |
| Chardonneret élégant; Goldfinch (406) | European/Gray-crowned Goldfinch; avibase-1B235E00 | European Goldfinch; Carduelis carduelis; avibase-59353A05 |
| Yellow wagtail sp. (281) | Western/Eastern Yellow Wagtail; avibase-1F56DC34 | Western Yellow Wagtail; Motacilla flava; avibase-5983D677 |
| Redpoll &#124; redpoll sp. (410) | Common/Lesser Redpoll group; avibase-3D1C0668 | Redpoll; Acanthis flammea; avibase-B6C8DDB2 |
| Courlis corlieu; Whimbrel (173) | Hudsonian/Eurasian Whimbrel; avibase-F9305BAA | Eurasian Whimbrel; Numenius phaeopus; avibase-082F3A63 |
| Cassenoix moucheté | Northern/Southern Nutcracker; avibase-76C74B10 | Northern Nutcracker; Nucifraga caryocatactes; avibase-D9B001DF |

The generic Trektellen yellow-wagtail label excludes Eastern Yellow Wagtail and maps to Western Yellow Wagtail at species level. Blue-headed Wagtail (Trektellen ID 282) is specifically the nominate subspecies Motacilla flava flava (avibase-876F7E82). Historical Bergeronnette printanière remains at Western Yellow Wagtail species level because that source label does not specify a subspecies. Lesser Redpoll labels remain mapped to the AviList cabaret subspecies; the generic Redpoll entry maps to the complete species. Counts and source labels are unchanged. The historical reference already spells Cassenoix moucheté correctly; the garbled accent in the pasted text does not require changing the workbook.

## Distinctions still broadened or merged

These are comparisons against the complete pinned checklist, not assumptions about what a newer eBird release might contain. Its many species-pair/hybrid/subspecies concepts were considered; none supplies the missing exact size/identification sets.

| Historical French labels | Trektellen English labels (IDs) | eBird export target | Information lost in count.csv |
| --- | --- | --- | --- |
| Goéland indéterminé; Mouette indéterminée | small gull sp. (989); large gull sp. (990) | gull sp.; larus; avibase-8D04DAAF | Source gull size/type distinctions. There is no small/large gull sp. pair; white-winged gull sp. is a different criterion. French names and size groups are not asserted to be exact synonyms. |
| Limicole indéterminé; limicole indéterminé; petit limicole indéterminé | wader sp. (672); small wader (2313) | shorebird sp.; shoreb1; avibase-7FC8B7ED | Small versus unspecified shorebird. Large shorebird sp. exists but cannot represent the small group. Capitalization variants alone lose no biological distinction. |
| Rapace indéterminé | raptor sp. (997); MediumRaptor (1150) | diurnal raptor sp.; diurap1; avibase-0C24147B | Medium versus unspecified raptor. No matching medium-size group. |
| Busard indéterminé | harrier sp. (584); Hen/Montagu's/Pallid Harrier (1102) | harrier sp.; harrie1; avibase-C235C72D | The three-candidate identification set broadens to all harriers. Hen/Montagu and Pallid/Montagu pair concepts each omit a candidate. |
| Bouvreuil pivoine; Bouvreuil trompeteur | Bullfinch (419) | Eurasian Bullfinch; eurbul; avibase-24764DC7 | Trumpeting-call distinction. The label alone cannot establish subspecies identity; do not assign a subspecies solely from this name. |
| — | Hobby / Red-footed Falcon (1099) | small falcon sp.; smafal; avibase-37EE6EA4 | Two-candidate set broadens. Amur Falcon/Eurasian Hobby is a different pair. |
| — | Cattle Egret / Little Egret (4868) | white egret sp.; whiegr1; avibase-D916AABA | Two-candidate set broadens. Little Egret × Western Cattle-Egret is a hybrid concept, not this unresolved identification. |

Exact available slash mappings (e.g. Common/Lesser Kestrel, Lesser/Greater Spotted Eagle, Tree/Olive-backed Pipit and Common/Pallid Swift) remain exact. Ordinary French and English synonyms for one species are not treated as lost distinctions.

The `source_taxa` array documents the variants of a concept, but cannot identify which variant belongs to an individual count once variants share a taxon_id. Recover that distinction by joining count.source_count_id to interim/processed/observations.csv.observation_id, which retains each original label and native species ID. We keep the requested simple count schema; re-export to eBird does not recover more precise identities from a broad group automatically. Annual PDF totals remain independent evidence.

## No-species entries and exclusions

Historical `Aucune espèce` (255 entries, all numerical zero) is excluded from count.csv and taxonomy.csv. The associated retained survey remains and its remark states that an explicit no-species entry was recorded. This is source evidence, not an inference of absence for every bird taxon. Surveys containing only non-bird entries also remain, without an invented no-species annotation.

Non-birds remain in the raw files and complete audit. `excluded_counts.csv` gives row-level exclusion reasons and `reconciliation.csv` balances source totals against retained birds, non-birds, no-species entries and overlapping-period exclusions.

The local research command `scripts/review/review_taxonomy.py` refreshes the review CSV after rebuilding; it is not shipped with the public core. Its quantities are complete source quantities (including overlap entries), not necessarily the released totals. Reassess group mappings when the pinned checklist is upgraded. The English/scientific names and IDs above can be verified directly in [the downloaded checklist](../taxonomy/reference/ebird_clements_2025_integrated_checklist.csv).

## Checklist maintenance

Observations are identified by their **Avibase concept id** (`avibase_id`), stable across checklists and versions. `taxonomy/source_taxa.csv` maps each source name or id to it, once; names, ranks and families then come from the reference checklists, never typed by hand: AviList first, eBird/Clements where AviList has no entry (it lists only species and subspecies) or leaves a field empty.

Where AviList and eBird draw a species differently, the mapping follows AviList: Hooded Crow and Carrion Crow are mapped to AviList's subspecies *Corvus corone cornix* and *C. c. corone* (eBird keeps them as two species). Rows marked `review` in `source_taxa.csv` are the judgement calls worth a second look.

**Upgrading a checklist:** add the new file to `taxonomy/reference/`, update `AVILIST_FILE` / `EBIRD_FILE` and the version labels in `src/defile_dataset/taxonomy.py`, rebuild. The check *Avibase ids in the checklists* lists every id the new versions no longer contain (typically after a split): re-map those rows. **A new Trektellen species** (an id not in `source_taxa.csv`) fails the check *Taxa in source_taxa.csv*: add a row for it.
