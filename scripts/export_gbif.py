#!/usr/bin/env python3
"""Convert the current dataset CSVs into Event and Occurrence CSVs for IPT."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from defile_dataset.consolidate import local_dates
from defile_dataset.site import COUNTRY_CODE, LATITUDE, LONGITUDE, SITE_NAME
from defile_dataset.taxonomy import EBIRD_FILE, EBIRD_VERSION

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--input", type=Path, default=Path("output/zenodo"))
parser.add_argument("--out", type=Path, default=Path("output/gbif"))
parser.add_argument(
    "--ebird-checklist",
    type=Path,
    default=Path(__file__).resolve().parents[1] / EBIRD_FILE,
    help="Pinned eBird/Clements checklist; taxa are joined by exact Avibase concept ID.",
)
parser.add_argument(
    "--zenodo-doi",
    default=json.loads((Path(__file__).resolve().parents[1] / "config/gbif.json").read_text())[
        "zenodo_doi"
    ],
    help="Release DOI from config/gbif.json, bare or as a doi.org URL; empty string omits it.",
)
parser.add_argument(
    "--coordinate-uncertainty-m",
    type=float,
    help="Reviewed uncertainty radius for the represented observation area, in metres.",
)
args = parser.parse_args()

# Read the canonical CSVs; counts inherit timing only when their override is missing.
count = pd.read_csv(args.input / "count.csv", low_memory=False)
survey = pd.read_csv(args.input / "survey.csv")
taxonomy = pd.read_csv(args.input / "taxonomy.csv")
# Prefer eBird names only for the same Avibase concept, never by a similar name.
ebird = pd.read_csv(args.ebird_checklist, low_memory=False).set_index("taxon concept ID")
# Missing subspecies English labels follow the eBird parent species, not an older synonym.
ebird["English name"] = ebird["English name"].fillna(
    (
        ebird["scientific name"]
        .str.split()
        .str[:2]
        .str.join(" ")
        .map(ebird.loc[ebird.category.eq("species")].set_index("scientific name")["English name"])
        .astype("string")
        + " ("
        + ebird["scientific name"].str.split().str[2].astype("string")
        + ")"
    ).where(ebird.category.eq("subspecies"))
)
ebird = ebird.loc[ebird.index.notna()].reindex(taxonomy.taxon_id)
for target, source in {
    "scientific_name": "scientific name",
    "english_name": "English name",
    "taxon_rank": "category",
    "order": "order",
    "family": "family",
}.items():
    taxonomy[target] = pd.Series(ebird[source].to_numpy(), index=taxonomy.index).combine_first(
        taxonomy[target]
    )
taxonomy["family"] = taxonomy.family.str.replace(r"\s*\(.*\)$", "", regex=True)
taxonomy["taxonomy_source"] = taxonomy.taxonomy_source.where(
    ebird["scientific name"].isna().to_numpy(), EBIRD_VERSION
)
rows = count.merge(
    survey[["survey_id", "datetime"]],
    on="survey_id",
    how="left",
    suffixes=("", "_survey"),
    validate="many_to_one",
)
rows["timing"] = rows.datetime.fillna(rows.datetime_survey)
rows["date"] = local_dates(rows.timing)
rows["eventID"] = "defile:2422:survey:" + rows.survey_id
unlinked = rows.survey_id.isna()
rows.loc[unlinked, "eventID"] = "defile:2422:unlinked-day:" + rows.loc[unlinked, "date"]

# Preserve native survey intervals, including empty/non-counting surveys and overnight windows.
events = survey.copy()
complete = events.survey_complete.astype(str).str.lower().eq("true")
stopped = events.weather_stop.astype(str).str.lower().eq("true")
inferred = events.survey_comment.fillna("").str.startswith(
    ("Empty interval inferred", "Minute-scale boundary gap")
)
properties = events[["survey_complete", "weather_stop"]].assign(
    survey_complete=complete,
    weather_stop=stopped.where(stopped),
    coverage_basis=pd.Series("inferred_empty_interval", index=events.index).where(inferred),
)
events["eventID"] = "defile:2422:survey:" + events.survey_id
events["eventDate"] = events.datetime
events["eventRemarks"] = np.select(
    [stopped, ~complete, inferred],
    [
        "Weather stop: no counting possible; passage was not measured. No taxon absence inferred.",
        "Incomplete count: count data or coverage are incomplete. No taxon absence inferred.",
        "Empty interval inferred from the recording convention; continuous counting assumed, "
        "attendance not independently verified. No taxon absence inferred.",
    ],
    "Complete count: the birds seen passing were recorded.",
)
events["dynamicProperties"] = [
    json.dumps({key: value for key, value in row.items() if pd.notna(value)}, ensure_ascii=False)
    for row in properties.to_dict("records")
]
events = events[["eventID", "eventDate", "eventRemarks", "dynamicProperties"]]
fallback = (
    rows.loc[unlinked, ["eventID", "date"]].drop_duplicates().rename(columns={"date": "eventDate"})
)
fallback[
    "eventRemarks"
] = "Date-level association for unlinked counts; no survey or observed effort inferred."
fallback["dynamicProperties"] = '{"event_origin": "unlinked_count_date"}'
events = pd.concat([events, fallback], ignore_index=True)
events["countryCode"] = COUNTRY_CODE
events["locality"] = SITE_NAME
events["locationID"] = "defile:2422:site"
events["decimalLatitude"] = LATITUDE
events["decimalLongitude"] = LONGITUDE
events["geodeticDatum"] = "WGS84"
events["coordinateUncertaintyInMeters"] = args.coordinate_uncertainty_m
events["locationRemarks"] = (
    "Configured count point used to locate the migration monitoring site; coordinates are not "
    "individual bird positions. Historical/alternate count locations remain to be reviewed."
)
events["samplingProtocol"] = "Visual counts of migrating birds."
events.loc[events.eventID.isin(fallback.eventID), "samplingProtocol"] = pd.NA

# Each released category row becomes one occurrence with its own numerical quantity.
occurrences = rows.merge(taxonomy, on="taxon_id", validate="many_to_one")
occurrences["occurrenceID"] = "defile:2422:count:" + occurrences.count_id
occurrences["individualCount"] = occurrences["count"].astype("Int64")
occurrences["eventDate"] = occurrences.timing
occurrences["basisOfRecord"] = "HumanObservation"
# GBIF reads individualCount=0 as an absence: zero category quantities stay in count.csv only.
present = occurrences["count"].gt(0) | occurrences.count_estimation.eq("presence")
occurrences = occurrences.loc[present].copy()
occurrences["occurrenceStatus"] = "present"
occurrences["taxonID"] = occurrences.taxon_id
occurrences["taxonConceptID"] = "https://avibase.ca/" + occurrences.taxon_id.str.removeprefix(
    "avibase-"
)
occurrences["scientificName"] = occurrences.scientific_name
occurrences["vernacularName"] = occurrences.english_name
occurrences["taxonRank"] = occurrences.taxon_rank.where(
    occurrences.taxon_rank.isin(["species", "subspecies", "genus", "family", "order", "class"])
)
occurrences["nameAccordingTo"] = occurrences.taxonomy_source
occurrences["kingdom"] = "Animalia"
occurrences["phylum"] = "Chordata"
occurrences["class"] = "Aves"
occurrences["taxonRemarks"] = (
    "eBird/Clements category: "
    + occurrences.taxon_rank
    + "; original Avibase concept retained without inferring a species identification."
).where(occurrences.taxonRank.isna())
occurrences["sex"] = occurrences.sex.where(occurrences.sex.isin(["male", "female"]))
occurrences["lifeStage"] = occurrences.age.where(occurrences.age.isin(["adult", "juvenile"]))
occurrences["behavior"] = occurrences.direction.map(
    {
        "main": "Migration in main count direction",
        "reverse": "Migration in reverse count direction",
        "local": "Local/non-migrating",
    }
)
occurrences["occurrenceRemarks"] = occurrences.direction.map(
    {
        "main": "Quantity for the main migration direction.",
        "reverse": "Quantity for the reverse migration direction; not part of main-direction migration totals.",
        "local": "Quantity for local/non-migrating birds; not part of migration totals.",
    }
) + occurrences.count_estimation.map(
    {
        "approximate": " Approximate count.",
        "minimum": " More than the recorded number; individualCount is a lower bound.",
        "presence": " Presence without a numerical count.",
    }
).fillna(
    ""
)
properties = ["direction", "count_estimation", "age"]
occurrences["dynamicProperties"] = [
    json.dumps({key: value for key, value in row.items() if pd.notna(value)}, ensure_ascii=False)
    for row in occurrences[properties].to_dict("records")
]
occurrences = occurrences[
    [
        "eventID",
        "occurrenceID",
        "eventDate",
        "basisOfRecord",
        "occurrenceStatus",
        "individualCount",
        "taxonID",
        "taxonConceptID",
        "scientificName",
        "vernacularName",
        "taxonRank",
        "nameAccordingTo",
        "kingdom",
        "phylum",
        "class",
        "order",
        "family",
        "taxonRemarks",
        "sex",
        "lifeStage",
        "behavior",
        "occurrenceRemarks",
        "dynamicProperties",
    ]
]
# Repeat geography on Occurrences so independent table imports retain the site context.
geography = [
    "countryCode",
    "locality",
    "locationID",
    "decimalLatitude",
    "decimalLongitude",
    "geodeticDatum",
    "coordinateUncertaintyInMeters",
    "locationRemarks",
]
occurrences = occurrences.merge(
    events[["eventID", *geography]], on="eventID", validate="many_to_one"
)
if args.zenodo_doi:
    reference = "https://doi.org/" + args.zenodo_doi.removeprefix("https://doi.org/")
    events["references"] = reference
    occurrences["references"] = reference

# Write the two source tables to import into IPT.
args.out.mkdir(parents=True, exist_ok=True)
events.to_csv(args.out / "event.csv", index=False, encoding="utf-8")
occurrences.to_csv(args.out / "occurrence.csv", index=False, encoding="utf-8")
(args.out / "README.md").write_text(
    (Path(__file__).resolve().parents[1] / "docs/templates/gbif-readme.md").read_text(),
    encoding="utf-8",
)
print(
    f"Wrote {len(events)} Events to {args.out / 'event.csv'} and {len(occurrences)} Occurrences to {args.out / 'occurrence.csv'}."
)
if not args.zenodo_doi:
    print(
        "Zenodo reference omitted: rerun with --zenodo-doi DOI once the release DOI is reserved."
    )
