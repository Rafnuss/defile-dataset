"""Check one-to-one survey/count mapping, including unknown quantities and empty events."""
import json
from pathlib import Path
import subprocess
import sys

import pandas as pd
import pytest


@pytest.fixture
def export_input(tmp_path):
    (tmp_path / 'dataset').mkdir()
    pd.DataFrame([
        ['T1-normal', 'T1', 'S1', 'bird', '2024-07-31T22:30:00Z', 5, 'normal', None, 'I', 'M', None],
        ['T1-reverse', 'T1', 'S1', 'bird', '2024-07-31T22:30:00Z', 2, 'reverse', None, 'I', 'M', None],
        ['T1-local', 'T1', 'S1', 'bird', '2024-07-31T22:30:00Z', 3, 'local', None, 'I', 'M', None],
        ['H1-normal', 'H1', 'S1', 'bird', None, 7, 'normal', None, None, None, None],
        ['T2-normal', 'T2', None, 'bird', '2024-08-02', 4, 'normal', None, None, None, None],
        ['T3-normal', 'T3', None, 'bird', '2024-08-02', None, 'normal', 'x', None, None, None],
        ['T4-normal', 'T4', None, 'bird', '2024-08-02', 0, 'normal', None, None, None, None],
    ], columns=['count_id', 'source_count_id', 'survey_id', 'taxon_id', 'datetime', 'count', 'count_category', 'count_estimation', 'age', 'sex', 'plumage']).assign(remark='Private source narrative', remark_processing='Detailed correction').to_csv(tmp_path / 'dataset/count.csv', index=False)
    pd.DataFrame([
        ['S1', '2024-07-31T22:00:00Z/2024-08-01T23:00:00Z', 'trektellen', 'complete'],
        ['S2', '2024-08-01T10:00:00Z/2024-08-01T11:00:00Z', 'trektellen', 'partial'],
        ['S3', '2024-08-02T22:00:00Z/2024-08-03T22:00:00Z', 'curated', 'none'],
    ], columns=['survey_id', 'datetime', 'recording_era', 'survey_coverage']).assign(survey_coverage_comment='Reviewed coverage', weather='Source weather narrative', observers='Observer names', temperature=12).to_csv(tmp_path / 'dataset/survey.csv', index=False)
    pd.DataFrame([['bird', 'Milvus milvus', 'species', 'AviList 2025']], columns=['taxon_id', 'scientific_name', 'taxon_rank', 'taxonomy_source']).to_csv(tmp_path / 'dataset/taxonomy.csv', index=False)
    return tmp_path


def test_export_preserves_survey_and_count_rows(export_input):
    script = Path(__file__).parents[1] / 'scripts/export_gbif.py'
    result = subprocess.run([sys.executable, str(script), '--input', str(export_input / 'dataset'), '--out', str(export_input / 'gbif')], text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    events = pd.read_csv(export_input / 'gbif/event.csv').set_index('eventID')
    occurrences = pd.read_csv(export_input / 'gbif/occurrence.csv').set_index('occurrenceID')
    assert len(events) == 4 and len(occurrences) == 7
    assert occurrences.individualCount.sum() == 21
    assert occurrences.loc['defile:2422:count:T1-normal', 'eventID'] == 'defile:2422:survey:S1'
    assert occurrences.loc['defile:2422:count:T1-normal', 'eventDate'] == '2024-07-31T22:30:00Z'
    assert occurrences.loc['defile:2422:count:H1-normal', 'eventDate'] == events.loc['defile:2422:survey:S1', 'eventDate']
    assert events.loc['defile:2422:survey:S1', 'eventDate'] == '2024-07-31T22:00:00Z/2024-08-01T23:00:00Z'
    properties = json.loads(occurrences.loc['defile:2422:count:T1-normal', 'dynamicProperties'])
    assert properties['count_category'] == 'normal' and properties['source_count_id'] == 'T1'
    assert properties['age'] == 'I' and occurrences.loc['defile:2422:count:T1-normal', 'sex'] == 'male'
    assert set(properties) == {'source_count_id', 'count_category', 'age'}
    assert 'Private source narrative' not in occurrences.to_csv() and 'Detailed correction' not in occurrences.to_csv()
    assert occurrences.loc['defile:2422:count:T2-normal', 'eventDate'] == '2024-08-02'
    assert occurrences.loc['defile:2422:count:T2-normal', 'eventID'] == 'defile:2422:unlinked-day:2024-08-02'
    assert 'sampleSizeValue' not in events.columns
    assert json.loads(events.loc['defile:2422:survey:S2', 'dynamicProperties'])['survey_coverage'] == 'partial'
    assert json.loads(events.loc['defile:2422:survey:S3', 'dynamicProperties'])['survey_coverage'] == 'none'
    assert set(json.loads(events.loc['defile:2422:survey:S2', 'dynamicProperties'])) == {'survey_coverage', 'survey_coverage_comment'}
    assert 'partial' in events.loc['defile:2422:survey:S2', 'eventRemarks']
    assert 'Observer names' not in events.to_csv() and 'Source weather narrative' not in events.to_csv()
    assert pd.isna(events.loc['defile:2422:unlinked-day:2024-08-02', 'samplingProtocol'])
    assert not occurrences.eventID.isin(['defile:2422:survey:S2', 'defile:2422:survey:S3']).any()
    assert pd.isna(occurrences.loc['defile:2422:count:T3-normal', 'individualCount'])
    assert occurrences.loc['defile:2422:count:T3-normal', 'occurrenceStatus'] == 'present'
    assert occurrences.loc['defile:2422:count:T4-normal', 'individualCount'] == 0
    assert pd.isna(occurrences.loc['defile:2422:count:T4-normal', 'occurrenceStatus'])
    assert occurrences.eventID.isin(events.index).all()
    assert occurrences.loc[occurrences.dynamicProperties.map(lambda value: json.loads(value)['count_category']).eq('reverse'), 'individualCount'].sum() == 2
    assert occurrences.loc[occurrences.dynamicProperties.map(lambda value: json.loads(value)['count_category']).eq('local'), 'individualCount'].sum() == 3
    assert set(path.name for path in (export_input / 'gbif').iterdir()) == {'README.md', 'event.csv', 'occurrence.csv'}
    assert (export_input / 'gbif/README.md').read_text() == (script.parents[1] / 'docs/templates/gbif-readme.md').read_text()
