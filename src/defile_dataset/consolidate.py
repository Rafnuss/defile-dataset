"""Count, native survey and taxonomy tables, projected from the complete audited source records."""

import html
import json

import pandas as pd

from defile_dataset.package import columns, descriptor

COUNT_COLUMNS = columns("count")
SURVEY_COLUMNS = columns("survey")
TAXON_COLUMNS = columns("taxonomy")
ERA = {"1966-2013": "notebook", "2014-2016": "spreadsheet", "2017-2021": "naturalist"}
NOTES = {
    "calendar_day_bounds": "Calendar-day bounds identify a non-survey day; no surveyed hours are known.",
    "no_time": "No recorded survey interval; retained with its date.",
    "no_survey": "Native survey header missing; retained with its date/time.",
    "time_outside_survey": "Entry time outside the native survey; retained at day level pending correction.",
    "untimed_in_timed_survey": "No entry time; retained at day level. Native association is in the audit.",
    "no_entries": "No count entries; this does not establish species absences.",
    "records_deleted": "Historical entries were deleted before the received reference workbook.",
}


def iso_time(values):
    """UTC ISO timestamps; date-only observations retain their collection date."""
    return values.dt.tz_convert("UTC").map(lambda t: t.isoformat().replace("+00:00", "Z") if pd.notna(t) else None)


def combine_text(data, fields, labels=False):
    """Retain every non-empty text field; processing messages never enter observer text."""
    result = pd.Series("", index=data.index, dtype="string")
    for field in fields:
        text = data[field].fillna("").astype(str).map(html.unescape)
        if labels:
            text = (field + ": " + text).where(text.ne(""), "")
        result += (" | " + text).where(text.ne(""), "")
    return result.str.removeprefix(" | ").replace("", pd.NA)


def processing_notes(data):
    text = data["flags"].fillna("").map(
        lambda flags: " ".join(NOTES.get(flag, flag) for flag in flags.split(";") if flag)
    )
    return text.replace("", pd.NA)



def category_counts(observations, components=None):
    """Split normal subgroups and movement categories without duplicating source quantities."""
    source = observations.assign(source_count_id=observations.observation_id)
    normal = source
    if components is not None:
        from defile_dataset.attributes import split_historical_counts
        normal = split_historical_counts(source, components)
    rows = [normal.assign(count_category="normal")]
    for category, field in (("reverse", "direction2"), ("local", "local")):
        part = source.loc[source[field].notna()].copy()
        part["count"], part["estimation"] = part[field], pd.NA
        # Historical descriptions qualify the main count, not reverse/local birds.
        part.loc[part.source.eq("historical"), ["age", "sex", "plumage"]] = pd.NA
        rows.append(part.assign(count_category=category))
    result = pd.concat(rows, ignore_index=True)
    result["observation_id"] += "-" + result.count_category
    return result

def consolidate(ds, taxonomy, components=None):
    """Release eligible categories and normal subgroups, preserving source timing and links."""
    s = ds.surveys.loc[ds.surveys.duplicate_of.isna()].copy()
    survey = s.reindex(columns=SURVEY_COLUMNS).copy()
    survey["datetime"] = iso_time(s.start) + "/" + iso_time(s.end)
    survey["recording_era"] = s.sheet.map(ERA).fillna("trektellen")
    # Empty historical days get their era from the date, not from a missing count sheet.
    historical = s.source.eq("historical")
    survey.loc[historical & s.sheet.eq("Pression observation"), "recording_era"] = s.loc[historical & s.sheet.eq("Pression observation"), "date"].dt.year.map(
        lambda year: "notebook" if year < 2014 else "spreadsheet" if year < 2017 else "naturalist"
    )
    survey["remark"] = s.remarks.map(lambda text: html.unescape(text) if pd.notna(text) else pd.NA)
    survey["observers"] = s.observers.map(lambda text: html.unescape(text) if pd.notna(text) else pd.NA)
    survey["weather"] = s.weather.map(lambda text: html.unescape(text) if pd.notna(text) else pd.NA)
    survey["remark_processing"] = processing_notes(s)
    daily_notes = historical & (s.observers.notna() | s.weather.notna() | s.remarks.notna())
    survey.loc[daily_notes, "remark_processing"] = survey.loc[daily_notes, "remark_processing"].fillna("") + " Historical narratives describe the day; they do not establish hourly attendance or constant weather."
    survey["remark_processing"] = survey.remark_processing.str.strip()

    markers = ds.observations.loc[ds.observations.taxon_kind.eq("no_species"), "survey_id"]
    marked = survey.survey_id.isin(markers)
    survey.loc[marked, "remark"] = (survey.loc[marked, "remark"].fillna("") +
        " An explicit 'no species' entry was recorded in the source.").str.strip()

    mapping = taxonomy.source_taxa.loc[taxonomy.source_taxa.kind.eq("bird")].copy()
    mapping["taxon_id"] = mapping.avibase_id
    o = ds.observations.loc[ds.observations.use_for_counts & ds.observations.taxon_kind.eq("bird")].copy()
    o = category_counts(o, components)
    for source, key in (("historical", "taxon_name_original"), ("trektellen", "trektellen_species_id")):
        lookup = mapping.loc[mapping.source.eq(source)].drop_duplicates(key).set_index(key).taxon_id
        mask = o.source.eq(source)
        o.loc[mask, "taxon_id"] = o.loc[mask, key].map(lookup)

    count = o.reindex(columns=COUNT_COLUMNS).copy()
    count["count_id"] = o.observation_id
    count["count_estimation"] = o.estimation
    count.loc[count.count_estimation.eq("x"), "count"] = pd.NA
    count["datetime"] = iso_time(pd.to_datetime(o.datetime, utc=True))
    # Preserve source associations; explicit dates prevent timing inheritance for fallbacks.
    linked = count.survey_id.isin(survey.survey_id)
    fallback = o.source.eq("trektellen") & o.time_resolution.eq("day")
    count.loc[~linked, "survey_id"] = pd.NA
    dated = (count.survey_id.isna() | fallback) & count.datetime.isna()
    count.loc[dated, "datetime"] = o.loc[dated, "date"].dt.strftime("%Y-%m-%d")
    count["remark"] = combine_text(o, ["detail", "details", "comment", "list_comment", "remark"], labels=True)
    notes = o.reindex(columns=["remark_processing"]).copy()
    notes["timing"] = processing_notes(o)
    count["remark_processing"] = combine_text(notes, ["remark_processing", "timing"])
    for resource in descriptor()["resources"]:
        if resource["name"] not in ("count", "survey"):
            continue
        data = count if resource["name"] == "count" else survey
        for field in resource["schema"]["fields"]:
            if field["type"] == "integer":
                data[field["name"]] = pd.array(data[field["name"]], dtype="Int64")


    taxon_rows = []
    resolved_taxa = taxonomy.taxa.set_index("avibase_id")
    for taxon_id, sources in mapping.loc[mapping.taxon_id.isin(count.taxon_id)].groupby("taxon_id", sort=True):
        resolved = resolved_taxa.reindex([sources.iloc[0].avibase_id]).iloc[0]
        source_fields = ["source", "taxon_name_original", "trektellen_species_id", "mapping_note", "review"]
        source_data = sources.reindex(columns=source_fields)
        source_values = source_data.astype(object).where(source_data.notna(), None).to_dict("records")
        taxon_rows.append({"taxon_id": taxon_id,
                           **resolved.to_dict(),
                           "trektellen_species_id": ",".join(str(int(value)) for value in sorted(sources.trektellen_species_id.dropna().unique())) or pd.NA,
                           "source_taxa": json.dumps(source_values, ensure_ascii=False)})
    taxa = pd.DataFrame(taxon_rows).reindex(columns=TAXON_COLUMNS)
    return count[COUNT_COLUMNS].reset_index(drop=True), survey[SURVEY_COLUMNS].reset_index(drop=True), taxa


def local_dates(values):
    """Select collection days in the declared site timezone, including midnight crossings."""
    start = values.str.split("/").str[0]
    dates = start.str[:10].copy()
    timed = start.str.contains("T", na=False)
    dates.loc[timed] = pd.to_datetime(start.loc[timed], utc=True, format="ISO8601").dt.tz_convert(descriptor()["x-calendarTimezone"]).dt.strftime("%Y-%m-%d")
    return dates


def daily_from_tables(count, survey):
    """Example derived view using only the two released tables; missing stays missing."""
    rows = count.merge(survey[["survey_id", "datetime"]], on="survey_id", how="left", suffixes=("", "_survey"), validate="many_to_one")
    rows["date"] = local_dates(rows.datetime.fillna(rows.datetime_survey))
    for category, field in (("reverse", "count_reverse"), ("local", "count_local")):
        rows[field] = rows["count"].where(rows.count_category.eq(category))
    rows["count"] = rows["count"].where(rows.count_category.eq("normal"))
    return rows.groupby(["date", "taxon_id"], sort=True).agg(
        count=("count", lambda values: values.sum(min_count=1)),
        count_reverse=("count_reverse", lambda values: values.sum(min_count=1)),
        count_local=("count_local", lambda values: values.sum(min_count=1)),
        records=("count_id", "size"),
    ).reset_index()


def validate_tables(count, survey, taxa, ds, components=None):
    """Return source-conservation results for the audit and publication gate."""
    from defile_dataset.checks import Check

    eligible = ds.observations.use_for_counts & ds.observations.taxon_kind.eq("bird")
    expected = ds.observations.loc[eligible].set_index("observation_id")
    source_ids = count.source_count_id
    original = expected.reindex(source_ids)
    native = original.survey_id.where(original.survey_id.isin(survey.survey_id)).reset_index(drop=True).astype('string')
    released = count.survey_id.reset_index(drop=True).astype('string')
    equal = released.eq(native).fillna(False) | (released.isna() & native.isna())
    native_links = pd.DataFrame(dict(count_id=count.count_id, released_survey_id=released, source_survey_id=native)).loc[~equal]
    ids = pd.Index(count.count_id)
    expected_rows = category_counts(expected.reset_index(), components)
    expected_ids = pd.Index(expected_rows.observation_id)
    missing = expected_ids.difference(ids)
    unexpected = ids.difference(expected_ids)
    duplicated = ids[ids.duplicated()].unique()
    bad = pd.DataFrame([dict(count_id=value, issue=issue) for issue, values in
                        [('missing_eligible_row', missing), ('unexpected_row', unexpected), ('duplicated_row', duplicated)] for value in values],
                       columns=['count_id', 'issue'])
    results = [Check('Eligible count categories retained once', 'fail' if len(bad) else 'pass',
                     f'{len(bad)} missing, unexpected or duplicate source IDs.', bad)]
    results.append(Check('Survey associations preserved', 'fail' if len(native_links) else 'pass',
                         f'{len(native_links)} survey associations differ from their available source survey.', native_links))
    for target, source in (("normal", "count"), ("reverse", "direction2"), ("local", "local")):
        exported = count["count"].where(count.count_category.eq(target)).groupby(source_ids).sum(min_count=1).reindex(expected.index).reset_index(drop=True)
        native = expected[source].reset_index(drop=True)
        if target == 'normal':
            native = native.mask(expected.estimation.eq('x').fillna(False).reset_index(drop=True))
        equal = exported.eq(native).fillna(False) | (exported.isna() & native.isna())
        bad = pd.DataFrame(dict(count_id=expected.index, released_value=exported, source_value=native)).loc[~equal]
        results.append(Check(f'{target} values preserved', 'fail' if len(bad) else 'pass',
                             f'{len(bad)} numerical values differ from their source. Presence-only main counts remain non-numerical.', bad))
    lineage = expected_rows.set_index("observation_id").reindex(count.count_id)
    equal = count.source_count_id.eq(lineage.source_count_id.reset_index(drop=True)) & count.count_category.eq(lineage.count_category.reset_index(drop=True))
    bad = count.loc[~equal, ["count_id", "source_count_id", "count_category"]]
    results.append(Check('Count category provenance preserved', 'fail' if len(bad) else 'pass',
                         f'{len(bad)} rows have incorrect source identities or categories.', bad))
    rows = count.merge(survey[["survey_id", "datetime"]], on="survey_id", how="left", suffixes=("", "_survey"))
    dates = local_dates(rows.datetime.fillna(rows.datetime_survey)).reset_index(drop=True)
    native = original.date.dt.strftime("%Y-%m-%d").reset_index(drop=True)
    bad = pd.DataFrame(dict(count_id=count.count_id, released_date=dates, source_date=native)).loc[dates.ne(native)]
    results.append(Check('Local collection dates preserved', 'fail' if len(bad) else 'pass',
                         f'{len(bad)} local dates differ after timing inheritance.', bad))
    return results
