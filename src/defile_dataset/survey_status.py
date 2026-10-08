"""Survey coverage from native intervals, comments and reviewed source decisions."""

import html
import re
import shlex
from pathlib import Path

import pandas as pd

FIELDS = ['survey_coverage', 'survey_coverage_comment']
REVIEW_COLUMNS = ['survey_id', 'date', 'issue', 'detail', 'weather', 'remarks']
INTERRUPTION_COLUMNS = ['interruption_id', 'datetime', 'time_precision', 'effect', 'note', 'native_survey_id', 'scope']
ALLOWED = {'survey_coverage': {'complete', 'partial', 'none', 'unknown'},
           'reason': {'weather', 'no_observer', 'logistics', 'other', 'unknown'}}


def classify_trektellen(surveys, observations, reviewed):
    """Classify coverage without changing bird records or native survey times."""
    surveys = surveys.copy()
    for field in FIELDS:
        if field not in surveys:
            surveys[field] = pd.NA
    recorded = observations.loc[observations.taxon_kind.isin(['bird', 'no_species']), 'survey_id']
    baseline = surveys.survey_coverage.isna() & surveys.survey_id.isin(recorded)
    surveys.loc[baseline, 'survey_coverage'] = 'complete'
    surveys.survey_coverage = surveys.survey_coverage.fillna('unknown')
    birds = observations.loc[observations.taxon_kind.eq('bird')]
    bird_groups = dict(tuple(birds.groupby('survey_id', sort=False)))
    native = surveys.loc[surveys.source.eq('trektellen')]
    findings, intervals = [], []
    for sid in sorted(set('T' + reviewed.count_id.astype(str)) - set(native.survey_id)):
        findings.append(dict(survey_id=sid, issue='reviewed_header_missing', detail='Reviewed count ID absent from exports.'))
    for i, row in native.iterrows():
        text = html.unescape(str(row.remarks)) if pd.notna(row.remarks) else ''
        weather = html.unescape(str(row.weather)) if pd.notna(row.weather) else ''
        decisions = reviewed.loc[reviewed.count_id.astype(str).eq(str(int(row.trektellen_count_id)))].to_dict('records')
        problems = []
        if text.count('[DEFILE') != len(re.findall(r'\[DEFILE\s+[^\]]*\]', text)):
            problems.append(('invalid_status_tag', 'Malformed DEFILE tag.'))
        for number, match in enumerate(re.finditer(r'\[DEFILE\s+([^\]]*)\]', text), 1):
            try:
                tag = dict(token.split('=', 1) for token in shlex.split(match[1]))
                assert set(tag) <= set(ALLOWED) | {'from', 'to'}
                assert tag.get('survey_coverage') in ALLOWED['survey_coverage']
                assert all(tag[f] in values for f, values in ALLOWED.items() if f in tag)
                assert ('from' in tag) == ('to' in tag)
                decision = dict(decision_id=f'{row.survey_id}-tag{number}', scope='period', datetime='',
                    time_precision='clock', native_weather=weather, native_remarks=text,
                    survey_coverage_comment=f"{tag.get('reason', 'unknown')}: {text}", **tag)
                if 'from' in tag:
                    assert tag['survey_coverage'] == 'none'
                    date = pd.Timestamp(row.start).tz_convert('Europe/Paris').strftime('%Y-%m-%d')
                    begin, end = [pd.Timestamp(date + ' ' + tag[f]).tz_localize('Europe/Paris') for f in ('from', 'to')]
                    assert row.start <= begin < end <= row.end
                    decision.update(scope='interval', datetime=begin.isoformat()+'/'+end.isoformat())
                decisions.append(decision)
            except (ValueError, AssertionError, TypeError):
                problems.append(('invalid_status_tag', match[0]))
        for d in decisions:
            if d['native_weather'] != weather or d['native_remarks'] != text:
                problems.append(('reviewed_source_changed', d['decision_id']))
        whole = [d for d in decisions if d['scope'] == 'period' and not d['datetime']]
        if len({d['survey_coverage'] for d in whole}) > 1:
            problems.append(('conflicting_classification', 'Whole-period decisions disagree.'))
        if problems:
            surveys.loc[i, 'survey_coverage'] = 'unknown'
        else:
            if whole:
                surveys.loc[i, 'survey_coverage'] = whole[0]['survey_coverage']
            comments = []
            for d in decisions:
                if d['survey_coverage_comment']:
                    comments.append(d['survey_coverage_comment'])
                if not d['datetime']:
                    continue
                begin, end = [pd.Timestamp(t).tz_convert('UTC') for t in d['datetime'].split('/')]
                if d['survey_coverage'] == 'none':
                    # A gap outside the header never makes that header partial.
                    if begin <= row.start and end >= row.end:
                        surveys.loc[i, 'survey_coverage'] = 'none'
                    elif begin < row.end and end > row.start:
                        surveys.loc[i, 'survey_coverage'] = 'partial'
                    intervals.append(dict(interruption_id=d['decision_id'], datetime=d['datetime'],
                        time_precision=d['time_precision'], effect='none', note=d['survey_coverage_comment'],
                        native_survey_id=row.survey_id, scope=d['scope']))
                    entries = bird_groups.get(row.survey_id, birds.iloc[:0])
                    times = pd.to_datetime(entries.datetime, utc=True)
                    if times.isna().any():
                        problems.append(('untimed_birds_near_interruption', 'Untimed birds cannot be checked against the gap.'))
                    if ((times >= begin) & (times < end)).any():
                        problems.append(('non_survey_with_bird_entries', 'Bird clocks occur in the inferred non-counting interval; retained.'))
            if comments:
                surveys.loc[i, 'survey_coverage_comment'] = ' | '.join(dict.fromkeys(comments))
            if surveys.loc[i, 'survey_coverage'] == 'partial' and not any(
                d['datetime'] and d['scope'] == 'interval' for d in decisions):
                problems.append(('partial_survey_hours_unknown', 'Partial coverage; exact gap/effort times unknown.'))
        if not decisions and re.search(r'\bHP\b|hors.?protocole|arrêt|arret|pas de spot|aucun oiseau|aucune visibilité|impossible|pas de comptage', weather+' '+text, re.I):
            problems.append(('ambiguous_status_text', 'Review comments for coverage interruptions.'))
        for issue, detail in problems:
            findings.append(dict(survey_id=row.survey_id, date=row.date, issue=issue,
                                 detail=detail, weather=row.weather, remarks=row.remarks))
    for i, row in surveys.iterrows():
        entries = bird_groups.get(row.survey_id, birds.iloc[:0])
        positive = entries['count'].fillna(0).gt(0)
        for field in ('direction2', 'local'):
            if field in entries:
                positive |= entries[field].fillna(0).gt(0)
        if 'estimation' in entries:
            positive |= entries.estimation.eq('x')
        if row.survey_coverage == 'none' and positive.any():
            surveys.loc[i, 'survey_coverage'] = 'unknown'
            findings.append(dict(survey_id=row.survey_id, date=row.date, issue='non_survey_with_bird_entries',
                detail='Positive/presence-only birds contradict no counting; coverage unknown, counts retained.'))
        if surveys.loc[i, 'survey_coverage'] == 'unknown':
            findings.append(dict(survey_id=row.survey_id, date=row.date, issue='unknown_coverage',
                                 detail=surveys.loc[i, 'survey_coverage_comment'] if pd.notna(surveys.loc[i, 'survey_coverage_comment']) else
                                     'Coverage cannot be established from the available records.'))
        if row.survey_coverage != 'none' and (pd.isna(row.start_original) or pd.isna(row.end_original)):
            findings.append(dict(survey_id=row.survey_id, date=row.date, issue='missing_survey_hours',
                                 detail='Original survey hours missing; calendar bounds are not effort.'))
    review = pd.DataFrame(findings, columns=REVIEW_COLUMNS)
    review = review.merge(surveys[['survey_id', 'start', 'end']], on='survey_id', how='left')
    review['duration_hours'] = (review.end-review.start).dt.total_seconds()/3600
    return surveys, pd.DataFrame(intervals, columns=INTERRUPTION_COLUMNS), review


def read_reviewed_status(root):
    return pd.read_csv(Path(root) / 'config/survey-status/trektellen-survey-status.csv', keep_default_na=False, dtype={'count_id': str})
