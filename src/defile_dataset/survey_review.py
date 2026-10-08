"""Evidence-based survey interruptions and coverage review."""

import json
from pathlib import Path

import pandas as pd

from defile_dataset.consolidate import ERA, local_dates


EMPTY_HOUR_NOTE = 'hour inside the declared day window with no record: counted, nothing seen'


def integrate_historical_gaps(survey, historical, breaks):
    """Subtract the union of released periods from each declared historical day window."""
    periods = survey.assign(date=local_dates(survey.datetime),
        start=pd.to_datetime(survey.datetime.str.split('/').str[0], utc=True),
        end=pd.to_datetime(survey.datetime.str.split('/').str[1], utc=True))
    days = dict(tuple(periods.groupby('date')))
    rows, audit = [], []
    for (sheet, date), day in historical.groupby(['sheet', 'date'], sort=True):
        begin, end = day.day_start.min(), day.day_end.max()
        gaps, cursor = [], begin
        native = days.get(date.strftime('%Y-%m-%d'), periods.iloc[:0])
        for start, stop in native.sort_values('start')[['start', 'end']].itertuples(index=False, name=None):
            if cursor < min(start, end):
                gaps.append((cursor, min(start, end)))
            cursor = max(cursor, stop)
        if cursor < end:
            gaps.append((cursor, end))
        for left, right in gaps:
            boundaries = {left, right}
            reviewed = breaks.loc[breaks.date.eq(date.strftime('%Y-%m-%d'))]
            for item in reviewed.itertuples(index=False):
                start, stop = [pd.Timestamp(t).tz_convert('UTC') for t in item.datetime.split('/')]
                boundaries.update(t for t in (start, stop) if left < t < right)
            boundaries = sorted(boundaries)
            for start, stop in zip(boundaries, boundaries[1:]):
                hours = (stop-start).total_seconds()/3600
                coverage = 'complete'
                note = ('Minute-scale boundary gap between recorded periods; exact times retained, continuous effort assumed.'
                        if hours <= 1/60 else
                        'Empty interval inferred from the declared day window and omitted empty-hour recording convention; attendance not independently verified.')
                if hours >= 3:
                    note += ' Long gap reviewed against available workbook notes; no timed interruption documented.'
                for item in reviewed.itertuples(index=False):
                    break_start, break_end = [pd.Timestamp(t).tz_convert('UTC') for t in item.datetime.split('/')]
                    if break_start <= start and stop <= break_end:
                        coverage = item.survey_coverage
                        note = item.note
                source_id = f'H{date:%Y%m%d}-{start.tz_convert("Europe/Paris"):%H%M%S}-declared-gap'
                interval = start.isoformat().replace('+00:00', 'Z') + '/' + stop.isoformat().replace('+00:00', 'Z')
                rows.append(dict(survey_id=source_id, datetime=interval, recording_era=ERA[sheet],
                    survey_coverage=coverage, survey_coverage_comment=note or pd.NA,
                    remark_processing=EMPTY_HOUR_NOTE if coverage == 'complete' else
                        'Break inside the declared day window; not counted.' if coverage == 'none' else
                        'Gap inside the declared day window; observation coverage unresolved, not a zero count.'))
                audit.append(dict(source_survey_id=source_id, sheet=sheet, date=date.strftime('%Y-%m-%d'),
                    datetime=interval, day_start=begin, day_end=end, hours=(stop-start).total_seconds()/3600,
                    survey_coverage=coverage, note=note))
    return pd.concat([survey, pd.DataFrame(rows).reindex(columns=survey.columns)], ignore_index=True), pd.DataFrame(audit)


def empty_survey_review(survey, count, observations, gaps):
    """Document all released periods without bird rows, independently of coverage."""
    rows = survey.loc[~survey.survey_id.isin(count.survey_id)].copy()
    rows['date'] = local_dates(rows.datetime)
    rows['duration_hours'] = (pd.to_datetime(rows.datetime.str.split('/').str[1], utc=True) -
                              pd.to_datetime(rows.datetime.str.split('/').str[0], utc=True)).dt.total_seconds()/3600
    rows['no_species_entries'] = rows.source_survey_id.map(
        observations.loc[observations.taxon_kind.eq('no_species')].groupby('survey_id').size()).fillna(0).astype(int)
    rows['review_class'] = 'empty_native_header'
    rows.loc[rows.no_species_entries.gt(0), 'review_class'] = 'explicit_no_species'
    rows.loc[rows.source_survey_id.isin(gaps.source_survey_id), 'review_class'] = 'declared_empty_interval'
    rows.loc[rows.source_survey_id.isin(gaps.source_survey_id) & rows.duration_hours.le(1/60), 'review_class'] = 'minute_boundary_gap'
    rows.loc[rows.source_survey_id.isin(gaps.source_survey_id) & rows.duration_hours.ge(3), 'review_class'] = 'long_declared_gap'
    rows.loc[rows.survey_coverage.eq('none'), 'review_class'] = 'non_counting'
    rows.loc[rows.survey_coverage.eq('unknown'), 'review_class'] = 'unresolved_coverage'
    missing_counts = rows.survey_coverage_comment.fillna('').str.contains(r'missing count data|counts? (?:were )?deleted', case=False)
    missing_counts |= rows.remark_processing.fillna('').str.contains('entries were deleted')
    rows.loc[missing_counts, 'review_class'] = 'missing_count_data'
    bird_dates = set(local_dates(count.datetime.fillna(count.survey_id.map(survey.set_index('survey_id').datetime))))
    rows['day_has_released_birds'] = rows.date.isin(bird_dates)
    return rows[['survey_id', 'source_survey_id', 'date', 'datetime', 'duration_hours', 'recording_era',
        'survey_coverage', 'survey_coverage_comment', 'review_class', 'day_has_released_birds',
        'no_species_entries', 'observers', 'weather', 'remark', 'remark_processing']].sort_values(['date', 'datetime', 'survey_id'])


def validate_historical_gaps(survey, count, gaps):
    """Check final gap rows against their declared bounds, other surveys and count links."""
    from defile_dataset.checks import Check

    periods = survey.assign(date=local_dates(survey.datetime),
        start=pd.to_datetime(survey.datetime.str.split('/').str[0], utc=True),
        end=pd.to_datetime(survey.datetime.str.split('/').str[1], utc=True))
    added = periods.loc[periods.survey_id.isin(gaps.survey_id)].merge(
        gaps[['survey_id', 'day_start', 'day_end']], on='survey_id', validate='one_to_one')
    outside = added.loc[(added.start < added.day_start) | (added.end > added.day_end) | (added.start >= added.end)]
    pairs = added[['survey_id', 'date', 'start', 'end']].merge(
        periods[['survey_id', 'date', 'start', 'end']], on='date', suffixes=('', '_other'))
    overlaps = pairs.loc[pairs.survey_id.ne(pairs.survey_id_other) & (pairs.start < pairs.end_other) & (pairs.end > pairs.start_other)]
    linked = count.loc[count.survey_id.isin(gaps.survey_id)]
    return [Check('Historical effort gaps inside declared windows', 'fail' if len(outside) else 'pass',
                  f'{len(outside)} gaps outside their day window.', outside),
            Check('Historical effort gaps do not overlap surveys', 'fail' if len(overlaps) else 'pass',
                  f'{len(overlaps)} overlapping gap/survey pairs.', overlaps),
            Check('Historical effort gaps have no counts', 'fail' if len(linked) else 'pass',
                  f'{len(linked)} count rows linked to added gaps.', linked)]


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
                unresolved = survey.loc[released_dates.eq(date)].empty or day.survey_coverage.eq('unknown').any() or pd.isna(hours)
                resolved = day.survey_coverage.isin(['none', 'partial']).any() or marker or survey.loc[released_dates.eq(date),'recording_era'].eq('curated').any()
                rows.append(dict(date=date, native_survey_ids=json.dumps(day.survey_id.tolist()), native_hours=hours,
                    bird_rows=int(entries.taxon_kind.eq('bird').sum()), bird_total=entries.loc[entries.taxon_kind.eq('bird'),'count'].sum(),
                    no_species_marker=bool(marker), reported_closure_days=window.reported_closure_days,
                    partial_threshold_hours=window.partial_threshold_hours,
                    assessment='unresolved' if unresolved or not resolved else 'linked_curated_evidence',
                    note=review_notes.get(date, ' | '.join(day.survey_coverage_comment.dropna().unique()) or
                        'Missing survey, short coverage or no-species marker alone does not establish a weather interruption.')))
    return pd.DataFrame(rows)
