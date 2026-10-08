# GBIF CSVs for IPT

Run `uv run python scripts/export_gbif.py` after building the dataset. The script converts the complete current count, survey and taxonomy tables into `event.csv` (Event core) and `occurrence.csv` (Occurrence extension). Import both into IPT as comma-separated UTF-8, with one header row and double-quote text delimiters; link them through `eventID` and map headers to the matching Darwin Core terms.

GBIF receives core fields and essential interpretive properties. The complete research CSVs, including weather, narratives, processing notes, native IDs, crosswalks and report text, remain in the companion research dataset; frozen publication through Zenodo is planned. Complete publisher, licence, attribution and dataset metadata in IPT. The initial proposal is the Swiss IPT with Vogelwarte as publisher, subject to agreement.

The current exporter derives occurrenceID and eventID from readable release IDs. These can change after corrections. Before the first GBIF publication, decide on persistent exported identities separately from the readable research IDs.
