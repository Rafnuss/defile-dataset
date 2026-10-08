#!/usr/bin/env python3
"""Convert the current dataset CSVs into Event and Occurrence CSVs for IPT."""
import argparse
import json
import shutil
from pathlib import Path

import pandas as pd

from defile_dataset.consolidate import local_dates
from defile_dataset.site import COUNTRY_CODE, SITE_NAME

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--input', type=Path, default=Path('output/dataset'))
parser.add_argument('--out', type=Path, default=Path('output/gbif'))
args = parser.parse_args()

# Read the canonical CSVs; counts inherit timing only when their override is missing.
count = pd.read_csv(args.input / 'count.csv', low_memory=False)
survey = pd.read_csv(args.input / 'survey.csv')
taxonomy = pd.read_csv(args.input / 'taxonomy.csv')
rows = count.merge(survey[['survey_id', 'datetime']], on='survey_id', how='left', suffixes=('', '_survey'), validate='many_to_one')
rows['timing'] = rows.datetime.fillna(rows.datetime_survey)
rows['date'] = local_dates(rows.timing)
rows['eventID'] = 'defile:2422:survey:' + rows.survey_id
unlinked = rows.survey_id.isna()
rows.loc[unlinked, 'eventID'] = 'defile:2422:unlinked-day:' + rows.loc[unlinked, 'date']

# Preserve native survey intervals, including empty/non-counting surveys and overnight windows.
events = survey.copy()
properties = events[['survey_coverage', 'survey_coverage_comment']]
events['eventID'] = 'defile:2422:survey:' + events.survey_id
events['eventDate'] = events.datetime
events['eventRemarks'] = 'Survey coverage: ' + events.survey_coverage.fillna('unknown') + '. Recorded interval does not establish observed effort or species absence.'
events['dynamicProperties'] = [json.dumps({key: value for key, value in row.items() if pd.notna(value)}, ensure_ascii=False) for row in properties.to_dict('records')]
events = events[['eventID', 'eventDate', 'eventRemarks', 'dynamicProperties']]
fallback = rows.loc[unlinked, ['eventID', 'date']].drop_duplicates().rename(columns={'date': 'eventDate'})
fallback['eventRemarks'] = 'Date-level association for unlinked counts; no survey or observed effort inferred.'
fallback['dynamicProperties'] = '{"survey_coverage": "unknown", "event_origin": "unlinked_count_date"}'
events = pd.concat([events, fallback], ignore_index=True)
events['countryCode'] = COUNTRY_CODE
events['locality'] = SITE_NAME
events['samplingProtocol'] = 'Visual counts of migrating birds.'
events.loc[events.eventID.isin(fallback.eventID), 'samplingProtocol'] = pd.NA

# Each released category row becomes one occurrence with its own numerical quantity.
occurrences = rows.merge(taxonomy, on='taxon_id', validate='many_to_one')
occurrences['occurrenceID'] = 'defile:2422:count:' + occurrences.count_id
occurrences['individualCount'] = occurrences['count'].astype('Int64')
occurrences['eventDate'] = occurrences.timing
occurrences['basisOfRecord'] = 'HumanObservation'
occurrences['occurrenceStatus'] = ''
present = occurrences['count'].gt(0) | occurrences.count_estimation.eq('x')
occurrences.loc[present, 'occurrenceStatus'] = 'present'
occurrences['taxonID'] = occurrences.taxon_id
occurrences['scientificName'] = occurrences.scientific_name
occurrences['taxonRank'] = occurrences.taxon_rank.where(occurrences.taxon_rank.isin(['species', 'subspecies', 'genus', 'family', 'order', 'class']))
occurrences['nameAccordingTo'] = occurrences.taxonomy_source
occurrences['sex'] = occurrences.sex.map({'M': 'male', 'F': 'female'})
occurrences['occurrenceRemarks'] = 'individualCount is the recorded quantity for count_category in dynamicProperties. No absence inferred from zero. Full source information is retained in the companion research dataset.'
properties = ['source_count_id', 'count_category', 'count_estimation', 'age']
occurrences['dynamicProperties'] = [json.dumps({key: value for key, value in row.items() if pd.notna(value)}, ensure_ascii=False) for row in occurrences[properties].to_dict('records')]
occurrences = occurrences[['eventID', 'occurrenceID', 'eventDate', 'basisOfRecord', 'occurrenceStatus', 'individualCount', 'taxonID', 'scientificName', 'taxonRank', 'nameAccordingTo', 'sex', 'occurrenceRemarks', 'dynamicProperties']]

# Write the two source tables to import into IPT.
args.out.mkdir(parents=True, exist_ok=True)
shutil.copyfile(Path(__file__).resolve().parents[1] / 'docs/templates/gbif-readme.md', args.out / 'README.md')
events.to_csv(args.out / 'event.csv', index=False, encoding='utf-8')
occurrences.to_csv(args.out / 'occurrence.csv', index=False, encoding='utf-8')
print(f"Wrote {len(events)} Events to {args.out / 'event.csv'} and {len(occurrences)} Occurrences to {args.out / 'occurrence.csv'}.")
