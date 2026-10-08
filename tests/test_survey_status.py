"""Coverage and effort semantics must preserve every bird record."""
import pandas as pd
from defile_dataset.survey_status import classify_trektellen, read_reviewed_status
from defile_dataset.survey_review import integrate_interruptions, observed_hours


def native(remark='', birds=True):
    surveys = pd.DataFrame([dict(survey_id='T1', source='trektellen', trektellen_count_id=1,
        date=pd.Timestamp('2027-08-01'), start=pd.Timestamp('2027-08-01T06:00Z'), end=pd.Timestamp('2027-08-01T16:00Z'),
        start_original=pd.Timestamp('2027-08-01T06:00Z'), end_original=pd.Timestamp('2027-08-01T16:00Z'), weather='', remarks=remark)])
    observations = pd.DataFrame([dict(survey_id='T1', taxon_kind='bird', datetime=pd.Timestamp('2027-08-01T07:00Z'), count=5)]) if birds else pd.DataFrame(columns=['survey_id', 'taxon_kind', 'datetime', 'count'])
    return surveys, observations, read_reviewed_status('.').iloc[:0]


def test_empty_hp_is_unknown_without_a_reviewed_decision():
    result, intervals, review = classify_trektellen(*native('HP brouillard', birds=False))
    assert result.survey_coverage.iloc[0] == 'unknown' and intervals.empty
    assert set(review.issue) == {'ambiguous_status_text', 'unknown_coverage'}


def test_full_closure_and_positive_bird_contradiction():
    s, o, r = native('[DEFILE survey_coverage=none reason=weather]', birds=False)
    result, intervals, review = classify_trektellen(s, o, r)
    assert result.survey_coverage.iloc[0] == 'none' and review.empty and intervals.empty
    _, birds, _ = native()
    before = birds.copy(deep=True)
    result, _, review = classify_trektellen(s, birds, r)
    assert result.survey_coverage.iloc[0] == 'unknown'
    assert 'non_survey_with_bird_entries' in set(review.issue)
    pd.testing.assert_frame_equal(birds, before)


def test_complete_zero_count_session():
    result, intervals, review = classify_trektellen(*native('[DEFILE survey_coverage=complete]', birds=False))
    assert result.survey_coverage.iloc[0] == 'complete' and review.empty and intervals.empty


def test_missing_original_hours_are_not_effort():
    s, o, r = native('[DEFILE survey_coverage=none]', birds=False)
    s[['start_original', 'end_original']] = pd.NaT
    assert classify_trektellen(s, o, r)[2].empty
    s.remarks = '[DEFILE survey_coverage=complete]'
    assert 'missing_survey_hours' in set(classify_trektellen(s, o, r)[2].issue)


def test_changed_source_withholds_decision_even_with_birds():
    s, o, r = native('new wording')
    r = pd.DataFrame([dict(decision_id='I1', count_id='1', scope='period', datetime='', time_precision='clock',
        survey_coverage='partial', survey_coverage_comment='stopped', native_weather='', native_remarks='old wording')])
    result, intervals, review = classify_trektellen(s, o, r)
    assert result.survey_coverage.iloc[0] == 'unknown' and intervals.empty
    assert 'reviewed_source_changed' in set(review.issue)


def test_conflicting_whole_period_tags_are_unknown():
    result, intervals, review = classify_trektellen(*native('[DEFILE survey_coverage=complete] [DEFILE survey_coverage=none]', birds=False))
    assert result.survey_coverage.iloc[0] == 'unknown' and intervals.empty
    assert 'conflicting_classification' in set(review.issue)


def test_explicit_gap_subtracts_only_its_duration(tmp_path):
    s, o, r = native('[DEFILE from=10:00 to=12:30 survey_coverage=none reason=weather]')
    result, intervals, review = classify_trektellen(s, o, r)
    assert review.empty and result.survey_coverage.iloc[0] == 'partial'
    assert intervals.effect.tolist() == ['none']
    assert observed_hours(result, intervals) == 7.5
    survey = result.assign(datetime='2027-08-01T06:00:00Z/2027-08-01T16:00:00Z', recording_era='trektellen')
    integrated, _ = integrate_interruptions(survey, o, tmp_path, intervals)
    assert len(integrated) == 1 and integrated.survey_coverage.iloc[0] == 'partial'


def test_untimed_birds_do_not_create_gap_times():
    s, o, r = native('[DEFILE from=10:00 to=12:30 survey_coverage=none]')
    o.datetime = pd.NaT
    result, intervals, review = classify_trektellen(s, o, r)
    assert result.survey_coverage.iloc[0] == 'partial' and intervals.effect.tolist() == ['none']
    assert 'untimed_birds_near_interruption' in set(review.issue)
    assert o['count'].sum() == 5


def test_partial_without_gap_times_has_unknown_hours():
    result, intervals, review = classify_trektellen(*native('[DEFILE survey_coverage=partial] Several stops; hours unknown.'))
    assert result.survey_coverage.iloc[0] == 'partial' and intervals.empty
    assert pd.isna(observed_hours(result, intervals))
    assert review.issue.tolist() == ['partial_survey_hours_unknown']


def test_gap_after_header_keeps_native_session_complete(tmp_path):
    s, o, r = native()
    r = pd.DataFrame([dict(decision_id='I1', count_id='1', scope='interval',
        datetime='2027-08-01T16:00Z/2027-08-01T18:00Z', time_precision='bounded',
        survey_coverage='none', survey_coverage_comment='Stopped at header end', native_weather='', native_remarks='')])
    result, intervals, review = classify_trektellen(s, o, r)
    assert result.survey_coverage.iloc[0] == 'complete' and review.empty
    integrated, _ = integrate_interruptions(result.assign(datetime='2027-08-01T06:00Z/2027-08-01T16:00Z', recording_era='trektellen'), o, tmp_path, intervals)
    assert integrated.survey_coverage.tolist() == ['complete', 'none']
    assert o['count'].sum() == 5
