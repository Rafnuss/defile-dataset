# GBIF CSVs for IPT

Run `uv run python scripts/export_gbif.py` after building the dataset. The script converts the complete current count, survey and taxonomy tables into `event.csv` (Event core) and `occurrence.csv` (Occurrence extension). Import both into IPT as comma-separated UTF-8, with one header row and double-quote text delimiters; link them through `eventID` and map headers to the matching Darwin Core terms.

GBIF receives core fields and essential interpretive properties. The intended GBIF licence is CC BY 4.0 for the first-party Event/Occurrence data, subject to rights-holder confirmation; record it in IPT/EML together with the approved attribution. The complete research CSVs, including weather, narratives, processing notes, native IDs and crosswalks, remain on GitHub/Zenodo. `report_text.csv` and `paper_text.csv` are excluded from GBIF and from the CC BY grant unless their source rights are cleared. The initial proposal is the Swiss IPT with Vogelwarte as publisher, subject to agreement.

The current exporter derives occurrenceID and eventID from readable release IDs. These can change after corrections. Before the first GBIF publication, decide on persistent exported identities separately from the readable research IDs.
