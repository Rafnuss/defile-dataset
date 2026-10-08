"""Audit outcomes, component accounting and coverage must retain scientific meaning."""
import pandas as pd


def test_status_report_keeps_native_edit_link_with_readable_survey_id():
    from defile_dataset.checks import Check
    from defile_dataset.report import _check_section
    rows = pd.DataFrame([dict(survey_id='T-20251020-0800', source_survey_id='T3221751', date='2025-10-20')])
    section = _check_section(Check('Status', 'warn', 'Review', rows, columns=('date', 'survey_id')))
    assert 'count/edit/3221751' in section
    assert 'count/edit/-20251020-0800' not in section
    assert 'T-20251020-0800' in section

from defile_dataset.audit import daily_coverage, quantity_components, summarize
from defile_dataset.checks import Check


def test_warning_is_independent_of_build_validity():
    assert summarize([Check('Daylight', 'warn', 'Inspect period')])['build_status'] == 'passed'
    assert summarize([Check('Unique ids', 'fail', 'Duplicated')])['build_status'] == 'blocked'


def test_quantity_components_show_remainder_and_conflict_without_changing_source():
    source = pd.DataFrame([dict(observation_id='H1', date='2020-09-01', sheet='2017-2021', row=2,
                                count=5, detail='1x mâle adulte / 2x femelle adulte', status='quantity_mismatch'),
                           dict(observation_id='H2', date='2020-09-02', sheet='2017-2021', row=3,
                                count=2, detail='3x adulte', status='quantity_mismatch')])
    from defile_dataset.attributes import historical_attributes
    from pathlib import Path
    CROSSWALK = pd.read_csv(Path("config/attributes/historical_attributes.csv"), dtype=str)
    source['details'] = source.detail
    _, parsed = historical_attributes(source, CROSSWALK)
    original = source.copy(deep=True)
    rows = quantity_components(parsed)
    assert rows.loc[rows.observation_id.eq('H-2017-2021-r2'), 'component_count'].tolist() == [1, 2, 2]
    assert rows.loc[rows.observation_id.eq('H-2017-2021-r3'), 'source_minus_detail'].tolist() == [-1]
    assert (rows.component_count >= 0).all()
    pd.testing.assert_frame_equal(source, original)


def test_final_daily_coverage_merges_periods_and_keeps_unknown_counts_missing():
    start = pd.Timestamp('2020-09-01T06:00:00Z')
    survey = pd.DataFrame(dict(survey_id=['H1','H2','H3'],
        datetime=[f'{a.isoformat()}/{b.isoformat()}' for a,b in [(start,start+pd.Timedelta(hours=3)),
            (start+pd.Timedelta(hours=1),start+pd.Timedelta(hours=2)), (start,start+pd.Timedelta(days=1))]],
        survey_coverage=['complete','complete','none']))
    count = pd.DataFrame(dict(count_id=['O1','O2'], survey_id=['H1','H2'], datetime=[None,None],
        count=[3,pd.NA], count_category=["normal"]*2))
    result = daily_coverage(count, survey).set_index('date')
    first = result.loc['2020-09-01']
    assert first.survey_hours == 3 and first.surveys == 2
    assert first.entries == 2 and first['count'] == 3 and pd.isna(first.count_reverse)
    assert first.complete == 2 and first.none == 1
    second = result.loc['2020-09-02']
    assert second.survey_hours == 0 and second.surveys == 0 and second.none == 1
    assert second.entries == 0 and pd.isna(second['count'])


def test_daily_coverage_uses_local_dates_dst_hours_and_unlinked_final_records():
    survey = pd.DataFrame(dict(survey_id=['S1'], survey_coverage=[pd.NA],
        datetime=['2020-10-24T22:00:00Z/2020-10-25T23:00:00Z']))
    count = pd.DataFrame(dict(count_id=['C1','C2','C3','C3-reverse'], survey_id=['S1',None,None,None],
        datetime=[None,'2020-10-26','2020-10-27','2020-10-27'], count=[0,pd.NA,2,1],
        count_category=['normal','normal','normal','reverse']))
    result = daily_coverage(count, survey).set_index('date')
    assert pd.isna(result.loc['2020-10-25','survey_hours'])
    assert result.loc['2020-10-25','unknown'] == 1
    assert result.loc['2020-10-25','count'] == 0
    assert pd.isna(result.loc['2020-10-26','count'])
    assert result.loc['2020-10-26','entries'] == 1 and result.loc['2020-10-26','surveys'] == 0
    assert pd.isna(result.loc['2020-10-26','survey_hours'])
    assert result.loc['2020-10-27','count_reverse'] == 1


def test_report_filters_use_complete_candidates_and_download_follows_table():
    from defile_dataset.report import render
    rows = pd.DataFrame({'duration_hours': [12.5, 15.5]*110})
    check = Check('Long surveys', 'warn', '', rows, key='long-surveys', group='Surveys',
                  filter_column='duration_hours', filter_threshold=15, file='validation_findings.csv')
    document = render([check], {})
    assert document.count('<tr data-filter-value=') == 220
    assert 'data-filter-value="12.5"' in document and 'data-sort="15.5"' in document
    assert 'finding-threshold' in document and 'value="15"' in document
    assert 'Suivis longs' in document and 'report-language' in document
    assert document.index('</table>') < document.index('href="validation_findings.csv"')
    assert 'aria-sort="none"' in document


def test_compact_survey_times_keep_next_day_marker_and_full_sort_value():
    from defile_dataset.report import render
    rows = pd.DataFrame({'date': pd.to_datetime(['2025-08-24']),
                         'start': pd.to_datetime(['2025-08-24T04:00:00Z']),
                         'end': pd.to_datetime(['2025-08-25T04:00:00Z']), 'night_minutes': [500.]})
    check = Check('Surveys into the night', 'warn', '', rows, key='surveys-into-the-night',
                  filter_column='night_minutes')
    document = render([check], {})
    assert '08-25 06:00' in document
    assert 'data-sort="2025-08-25 04:00:00+00:00"' in document


def test_empty_survey_duration_filter_allows_short_periods():
    from defile_dataset.report import render
    check = Check('Empty surveys', 'warn', '', pd.DataFrame({'duration_hours': [0.25, 2.0]}),
                  key='survey-status-unclassified_empty_header', filter_column='duration_hours')
    document = render([check], {})
    assert 'min="0"' in document and 'data-filter-value="0.25"' in document
    assert 'View day' in document


def test_entry_offset_filter_uses_minutes_and_default_tolerance():
    from defile_dataset.report import render
    check = Check('Entry times outside their source period', 'warn', '', pd.DataFrame({'outside_minutes': [5, 6]}),
                  key='entry-times-outside-their-source-period', filter_column='outside_minutes', filter_threshold=5)
    document = render([check], {})
    assert 'Outside period by more than (min)' in document and 'value="5"' in document
    assert 'data-filter-value="5"' in document and 'data-filter-value="6"' in document


def test_coverage_report_shows_final_daily_figure_and_no_old_coverage_tables():
    from defile_dataset.report import render
    coverage = pd.DataFrame(dict(date=pd.to_datetime(['2020-09-01']), year=[2020], day_of_year=[245],
        entries=[1], surveys=[1], survey_hours=[3], count=[pd.NA], count_reverse=[0], count_local=[pd.NA]))
    document = render([], {}, coverage=coverage,
                      coverage_season=dict(start_day_of_year=196, end_day_of_year=335))
    assert 'coverage-metric' in document and 'coverage/plotly.min.js' in document
    assert 'Plotly.react' in document and 'coverage-chart' in document
    assert '"start_day_of_year": 196, "end_day_of_year": 335' in document
    assert 'daily_coverage.csv' in document and 'coverage-download' in document
    assert 'Precision and missing attributes' not in document
    assert 'released_surveys' not in document and 'source_surveys' not in document
    assert 'yearly_coverage.csv' not in document
    assert '"count": null' in document and '"count_reverse": 0' in document
