"""Readable release IDs; original identities remain available for source tracing."""

import unicodedata

import pandas as pd

from defile_dataset.consolidate import ERA
from defile_dataset.site import TIMEZONE

PREFIX = {'notebook': 'B', 'spreadsheet': 'S', 'naturalist': 'N', 'trektellen': 'T', 'curated': 'C'}


def unique_names(names, order):
    """Number collisions in source order, independently of the table's row order."""
    rows = pd.DataFrame({'name': names, 'order': order}).sort_values('order', kind='stable')
    number = rows.groupby('name').cumcount() + 1
    rows['name'] += ('-' + number.astype(str).str.zfill(2)).where(number.gt(1), '')
    return rows.name.reindex(names.index)


def readable_ids(count, survey, observations, interruptions):
    """Name final records from local dates, recorded clocks and existing eBird codes."""
    count, survey, interruptions = count.copy(), survey.copy(), interruptions.copy()
    survey['source_survey_id'] = survey.survey_id
    start = pd.to_datetime(survey.datetime.str.split('/').str[0], utc=True).dt.tz_convert(TIMEZONE)
    calendar = survey.source_survey_id.str.endswith('-not-surveyed') | survey.remark_processing.fillna('').str.contains('Calendar-day bounds')
    day_interruptions = interruptions.loc[interruptions.time_precision.eq('day'), 'interruption_id']
    calendar |= survey.recording_era.eq('curated') & survey.source_survey_id.str.replace(r'-gap\d+$', '', regex=True).isin(day_interruptions)
    names = survey.recording_era.map(PREFIX) + '-' + start.dt.strftime('%Y%m%d')
    names += ('-' + start.dt.strftime('%H%M')).where(~calendar, '')
    survey['survey_id'] = unique_names(names, survey.source_survey_id)
    survey_map = survey.set_index('source_survey_id').survey_id
    count['survey_id'] = count.survey_id.map(survey_map)
    interruptions['native_survey_id'] = interruptions.native_survey_id.map(survey_map)

    source = observations.loc[observations.observation_id.isin(count.source_count_id)].copy()
    era = source.sheet.map(ERA).fillna('trektellen')
    names = era.map(PREFIX) + '-' + source.date.dt.strftime('%Y%m%d')
    clock = pd.to_datetime(source.datetime, utc=True).dt.tz_convert(TIMEZONE).dt.strftime('%H%M')
    # Historical entry clocks are recorded separately; day bounds are never entry times.
    historical_clock = source.time_local.astype('string').str.extract(r'(\d{2}):(\d{2})').fillna('')
    historical_clock = historical_clock[0] + historical_clock[1]
    clock = clock.fillna(historical_clock.replace('', pd.NA))
    interval_start = pd.Series(start.dt.strftime('%H%M').values, index=survey.source_survey_id)
    clock = clock.fillna(source.survey_id.map(interval_start).where(source.time_resolution.eq('interval')))
    names += ('-' + clock).fillna('')
    labels = source.taxon_name_original.map(lambda value: unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode())
    labels = labels.str.lower().str.replace(r'[^a-z0-9]+', '-', regex=True).str.strip('-')
    names += '-' + source.ebird_code.fillna(labels)
    source['readable_id'] = unique_names(names, source.observation_id)
    source_map = source.set_index('observation_id').readable_id
    # Preserve the existing subgroup/category suffixes on each derived row.
    suffix = pd.Series([value[len(original):] for value, original in zip(count.count_id, count.source_count_id)], index=count.index)
    count['count_id'] = count.source_count_id.map(source_map) + suffix
    return count, survey, interruptions
