"""Evidence-based survey interruptions and coverage review."""

import json
from pathlib import Path

import pandas as pd

from defile_dataset.consolidate import local_dates


def integrate_interruptions(survey, count, root, status_intervals=None):
    """Keep status on survey rows and add only documented non-counting gaps."""
    from defile_dataset.survey_status import INTERRUPTION_COLUMNS
    interruptions = status_intervals.fillna('').copy() if status_intervals is not None else pd.DataFrame(columns=INTERRUPTION_COLUMNS)
    survey = survey.copy()
    for field in ('survey_coverage', 'survey_coverage_comment'):
        if field not in survey:
            survey[field] = pd.NA
    survey.survey_coverage = survey.survey_coverage.fillna('unknown')
    for row in interruptions.itertuples(index=False):
        begin, end = [pd.Timestamp(t).tz_convert('UTC') for t in row.datetime.split('/')]
        native = survey.loc[local_dates(survey.datetime).eq(begin.tz_convert('Europe/Paris').strftime('%Y-%m-%d'))]
        starts = pd.to_datetime(native.datetime.str.split('/').str[0], utc=True, format='ISO8601')
        ends = pd.to_datetime(native.datetime.str.split('/').str[1], utc=True, format='ISO8601')
        if row.effect != 'none':
            continue
        for i in native.index[(starts < end) & (ends > begin)]:
            # The classifier already resolves contradictions with bird evidence.
            if survey.loc[i, 'survey_coverage'] == 'unknown':
                continue
            survey.loc[i, 'survey_coverage'] = 'none' if begin <= starts[i] and end >= ends[i] else 'partial'
            previous = survey.loc[i, 'survey_coverage_comment']
            notes = str(previous).split(' | ') if pd.notna(previous) else []
            survey.loc[i, 'survey_coverage_comment'] = ' | '.join(dict.fromkeys(notes + [row.note]))
        gaps = [(begin, end)]
        for start, stop in zip(starts, ends):
            pieces = []
            for left, right in gaps:
                if stop <= left or start >= right:
                    pieces.append((left, right))
                else:
                    if left < start:
                        pieces.append((left, start))
                    if stop < right:
                        pieces.append((stop, right))
            gaps = pieces
        # A full-day closure with a native header does not need calendar padding.
        if row.scope == 'day' and len(native):
            continue
        for number, (left, right) in enumerate(gaps, 1):
            survey = pd.concat([survey, pd.DataFrame([dict(survey_id=f'{row.interruption_id}-gap{number}',
                datetime=left.isoformat().replace('+00:00', 'Z')+'/'+right.isoformat().replace('+00:00', 'Z'),
                recording_era='curated', survey_coverage='none', survey_coverage_comment=row.note,
                remark_processing='Non-counting bounds; not observed effort or a zero bird count.')])], ignore_index=True)
    return survey, interruptions


def observed_hours(survey, interruptions=None):
    """Union actual effort; return unknown if partial/unknown coverage has no usable bounds."""
    periods = []
    for row in survey.itertuples():
        coverage = row.survey_coverage if pd.notna(row.survey_coverage) else 'unknown'
        if coverage == 'none':
            continue
        if coverage == 'unknown':
            return float('nan')
        pieces = [(row.start, row.end)]
        if coverage == 'partial':
            if interruptions is None:
                return float('nan')
            gaps = interruptions.loc[interruptions.native_survey_id.eq(row.survey_id) & interruptions.effect.eq('none')]
            overlapping = False
            for interval in gaps.datetime:
                left, right = [pd.Timestamp(t).tz_convert('UTC') for t in interval.split('/')]
                if left < row.end and right > row.start:
                    overlapping = True
                remaining = []
                for start, end in pieces:
                    if right <= start or left >= end:
                        remaining.append((start, end))
                    else:
                        if start < left:
                            remaining.append((start, left))
                        if right < end:
                            remaining.append((right, end))
                pieces = remaining
            if not overlapping:
                return float('nan')
        periods.extend(pieces)
    hours, last = 0, None
    for start, end in sorted(periods):
        hours += max(0, (end - max(start, last if last is not None else start)).total_seconds()/3600)
        last = max(end, last if last is not None else end)
    return hours


def interruption_review(survey, observations, root, interruptions=None):
    """Review gaps/short days without converting ambiguous absences into weather closures."""
    windows = pd.read_csv(Path(root) / 'config/audit-settings/report-season-windows.csv')
    native = survey.loc[~survey.recording_era.eq('curated')].copy()
    native['date'] = local_dates(native.datetime)
    starts = pd.to_datetime(native.datetime.str.split('/').str[0], utc=True, format='ISO8601')
    ends = pd.to_datetime(native.datetime.str.split('/').str[1], utc=True, format='ISO8601')
    native['start'], native['end'] = starts, ends
    native['hours'] = (ends-starts).dt.total_seconds()/3600
    observed = observations.assign(date=observations.date.dt.strftime('%Y-%m-%d'))
    observation_days = dict(tuple(observed.groupby('date', sort=False)))
    review_notes = pd.read_csv(Path(root) / 'config/audit-settings/interruption-review-notes.csv').set_index('date').note.to_dict()
    released_dates = local_dates(survey.datetime)
    rows = []
    for window in windows.itertuples(index=False):
        for date in pd.date_range(window.start, window.end).strftime('%Y-%m-%d'):
            day = native.loc[native.date.eq(date)]
            entries = observation_days.get(date, observed.iloc[:0])
            hours = observed_hours(day, interruptions)
            short = pd.isna(hours) or (pd.notna(window.partial_threshold_hours) and hours < window.partial_threshold_hours)
            marker = entries.taxon_kind.eq('no_species').any()
            if day.empty or short or marker or day.survey_coverage.isin(['none', 'partial', 'unknown']).any() or date in review_notes:
                rows.append(dict(date=date, native_survey_ids=json.dumps(day.survey_id.tolist()), native_hours=hours,
                    bird_rows=int(entries.taxon_kind.eq('bird').sum()), bird_total=entries.loc[entries.taxon_kind.eq('bird'),'count'].sum(),
                    no_species_marker=bool(marker), reported_closure_days=window.reported_closure_days,
                    partial_threshold_hours=window.partial_threshold_hours,
                    assessment='linked_curated_evidence' if day.survey_coverage.isin(['none', 'partial', 'unknown']).any() or survey.loc[released_dates.eq(date),'recording_era'].eq('curated').any() else 'unresolved',
                    note=review_notes.get(date, 'Missing survey, short coverage or no-species marker alone does not establish a weather interruption.')))
    return pd.DataFrame(rows)
