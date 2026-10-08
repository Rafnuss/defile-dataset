"""Non-counting evidence must not create overlapping effort or zero bird counts."""
import pandas as pd
from defile_dataset.survey_review import integrate_interruptions


def test_closure_links_existing_header_and_adds_only_uncovered_gap(tmp_path):
    folder = tmp_path / 'config/audit-settings'
    folder.mkdir(parents=True)
    events = pd.DataFrame([
        dict(interruption_id='I1', scope='day', datetime='2024-09-26T00:00:00+02:00/2024-09-27T00:00:00+02:00', time_precision='day', effect='none', reason='rain', evidence_status='documented', source_reference='report', evidence='no counting', note='Evidence: no counting. Calendar day.'),
        dict(interruption_id='I2', scope='interval', datetime='2024-09-27T10:00:00+02:00/2024-09-27T12:00:00+02:00', time_precision='clock', effect='none', reason='rain', evidence_status='documented', source_reference='native', evidence='stopped', note='stopped'),
    ])
    survey = pd.DataFrame([
        dict(survey_id='T1',datetime='2024-09-26T07:00:00Z/2024-09-26T15:00:00Z',recording_era='trektellen',survey_coverage='complete',weather='native',remark='unchanged'),
        dict(survey_id='T2',datetime='2024-09-27T07:00:00Z/2024-09-27T09:00:00Z',recording_era='trektellen',survey_coverage='complete',weather='rain',remark='stopped'),
        dict(survey_id='T3',datetime='2024-09-27T10:00:00Z/2024-09-27T11:00:00Z',recording_era='trektellen',survey_coverage='complete',weather='clear',remark='resumed'),
    ])
    counts = pd.DataFrame([dict(survey_id='T2',datetime='2024-09-27T07:30:00Z')])
    result, interruptions = integrate_interruptions(survey, counts, tmp_path, events)
    assert len(result) == 4
    assert result.set_index('survey_id').loc['T1','survey_coverage'] == 'none'
    assert result.set_index('survey_id').loc['T2','survey_coverage'] == 'partial'
    assert result.set_index('survey_id').loc['I2-gap1','datetime'] == '2024-09-27T09:00:00Z/2024-09-27T10:00:00Z'
    pd.testing.assert_frame_equal(result.iloc[:3][survey.columns.drop('survey_coverage')].reset_index(drop=True), survey.drop(columns='survey_coverage'))
    details = result.set_index('survey_id').survey_coverage_comment
    assert 'no counting' in details['T1'] and 'stopped' in details['T2']
    assert 'stopped' in details['I2-gap1']
    assert result.set_index('survey_id').loc['T3','survey_coverage'] == 'complete'
    assert len(counts) == 1


def test_inferred_workbook_day_links_report_without_duplicate_gap(tmp_path):
    folder = tmp_path / 'config/audit-settings'
    folder.mkdir(parents=True)
    events = pd.DataFrame([dict(interruption_id='I1', scope='day',
        datetime='2008-09-04T00:00:00+02:00/2008-09-05T00:00:00+02:00',
        time_precision='day', effect='none', reason='weather_unspecified',
        evidence_status='inferred', source_reference='report', evidence='9 closed days', note='inferred date')
    ])
    survey = pd.DataFrame([dict(survey_id='H20080904-not-surveyed',
        datetime='2008-09-03T22:00:00Z/2008-09-04T22:00:00Z', recording_era='notebook',
        survey_coverage='none', reason='weather', evidence_status='inferred')])
    counts = pd.DataFrame(columns=['survey_id', 'datetime'])
    result, interruptions = integrate_interruptions(survey, counts, tmp_path, events)
    assert len(result) == 1 and result.survey_coverage.iloc[0] == 'none'
    assert 'inferred' in result.survey_coverage_comment.iloc[0]
