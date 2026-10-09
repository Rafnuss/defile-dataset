"""Count, native survey and taxonomy tables, projected from the complete audited source records."""

import html
import json

import pandas as pd

from defile_dataset.movement_text import project_non_passage
from defile_dataset.package import columns, descriptor
from defile_dataset.read import EFFORT_SHEET
from defile_dataset.remark_text import clean_text
from defile_dataset.source_text import split_timed_counts

COUNT_COLUMNS = columns("count")
SURVEY_COLUMNS = columns("survey")
TAXONOMY_COLUMNS = columns("taxonomy")
ERA = {"1966-2013": "notebook", "2014-2016": "spreadsheet", "2017-2021": "naturalist"}
NOTES = {
    "calendar_day_bounds": "Calendar-day bounds: weather stopped counting all day; no hours were recorded.",
    "no_time": "No recorded survey interval; retained with its date.",
    "no_survey": "Native survey header missing; retained with its date/time.",
    "time_outside_survey": "Entry time outside the native survey; retained at day level pending correction.",
    "untimed_in_timed_survey": "No entry time; retained at day level. Native association is in the audit.",
    "no_entries": "No count entries; this does not establish species absences.",
    "records_deleted": "Historical entries were deleted before the received reference workbook.",
    "reviewed_time_clear": "Reviewed entry clock cleared; the linked survey supplies observation support.",
    "reviewed_time_interval": "Reviewed source range supplies observation support; no exact passage clock is assigned.",
    "reviewed_time_point": "Explicit source observation clock retained after timing review.",
    "reviewed_survey_link": "Observation linked to the existing survey containing its explicit source clock or range.",
}


def iso_time(values):
    """UTC ISO timestamps; date-only observations retain their collection date."""
    return values.dt.tz_convert("UTC").map(
        lambda t: t.isoformat().replace("+00:00", "Z") if pd.notna(t) else None
    )


def combine_text(data, fields):
    """Retain every non-empty text field; processing messages never enter observer text."""
    result = pd.Series("", index=data.index, dtype="string")
    for field in fields:
        text = clean_text(data[field].fillna("").astype(str).map(html.unescape)).fillna("")
        result += (" | " + text).where(text.ne(""), "")
    return result.str.removeprefix(" | ").str.strip().replace("", pd.NA)


def processing_notes(data):
    text = (
        data["flags"]
        .fillna("")
        .map(lambda flags: " ".join(NOTES.get(flag, flag) for flag in flags.split(";") if flag))
    )
    return text.replace("", pd.NA)


def category_counts(observations, components=None, taxonomy_rules=None):
    """Split normal subgroups and movement categories without duplicating source quantities."""
    source = observations.assign(source_count_id=observations.observation_id)
    source, movement_audit = project_non_passage(source)
    normal = source
    if components is not None:
        from defile_dataset.attributes import split_historical_counts

        # Transferred main counts must not be recreated from their original detail components.
        normal = split_historical_counts(
            source,
            components.loc[
                components.observation_id.isin(source.loc[source["count"].gt(0), "observation_id"])
            ],
        )
    normal = split_timed_counts(normal)
    taxonomy_audit = pd.DataFrame()
    if taxonomy_rules is not None:
        from defile_dataset.taxonomy_refinement import refine_taxonomy

        normal, taxonomy_audit = refine_taxonomy(normal, taxonomy_rules)
    rows = [normal.assign(count_category="normal")]
    for category, field in (("reverse", "direction2"), ("local", "local")):
        part = source.loc[source[field].notna()].copy()
        part["count"], part["estimation"] = part[field], pd.NA
        # Historical descriptions qualify the main count, not reverse/local birds.
        part.loc[part.source.eq("historical"), ["age", "sex", "plumage"]] = pd.NA
        rows.append(part.assign(count_category=category))
    result = pd.concat(rows, ignore_index=True)
    result["observation_id"] += "-" + result.count_category
    result.attrs["taxonomy_review"] = taxonomy_audit.to_dict("records")
    result.attrs["movement_review"] = movement_audit.to_dict("records")
    return result


def consolidate(ds, taxonomy, components=None):
    """Release eligible categories and normal subgroups, preserving source timing and links."""
    s = ds.surveys.loc[ds.surveys.duplicate_of.isna()].copy()
    survey = s.reindex(columns=SURVEY_COLUMNS).copy()
    survey["datetime"] = iso_time(s.start) + "/" + iso_time(s.end)
    survey["recording_era"] = s.sheet.map(ERA).fillna("trektellen")
    # Empty historical days get their era from the date, not from a missing count sheet.
    historical = s.source.eq("historical")
    survey.loc[historical & s.sheet.eq(EFFORT_SHEET), "recording_era"] = s.loc[
        historical & s.sheet.eq(EFFORT_SHEET), "date"
    ].dt.year.map(
        lambda year: "notebook" if year < 2014 else "spreadsheet" if year < 2017 else "naturalist"
    )
    survey["remark"] = s.remarks.map(lambda text: html.unescape(text) if pd.notna(text) else pd.NA)
    survey["observers"] = s.observers.map(
        lambda text: html.unescape(text) if pd.notna(text) else pd.NA
    )
    survey["weather"] = s.weather.map(
        lambda text: html.unescape(text) if pd.notna(text) else pd.NA
    )
    survey["remark_processing"] = processing_notes(s)
    daily_notes = historical & (s.observers.notna() | s.weather.notna() | s.remarks.notna())
    survey.loc[daily_notes, "remark_processing"] = (
        survey.loc[daily_notes, "remark_processing"].fillna("")
        + " Historical narratives describe the day; they do not establish hourly attendance or constant weather."
    )
    survey["remark_processing"] = clean_text(survey.remark_processing)
    for field in ("remark", "observers", "weather"):
        survey[field] = clean_text(survey[field])

    markers = ds.observations.loc[ds.observations.taxon_kind.eq("no_species"), "survey_id"]
    marked = survey.survey_id.isin(markers)
    survey.loc[marked, "remark"] = (
        survey.loc[marked, "remark"].fillna("")
        + " An explicit 'no species' entry was recorded in the source."
    ).str.strip()

    mapping = taxonomy.source_taxa.loc[taxonomy.source_taxa.kind.eq("bird")].copy()
    mapping["taxon_id"] = mapping.avibase_id
    o = ds.observations.loc[
        ds.observations.use_for_counts & ds.observations.taxon_kind.eq("bird")
    ].copy()
    o = category_counts(o, components, taxonomy.reviewed)
    for source, key in (
        ("historical", "taxon_name_original"),
        ("trektellen", "trektellen_species_id"),
    ):
        lookup = (
            mapping.loc[mapping.source.eq(source)].drop_duplicates(key).set_index(key).taxon_id
        )
        mask = o.source.eq(source)
        o.loc[mask, "taxon_id"] = (
            o.loc[mask, "taxon_id"].fillna(o.loc[mask, key].map(lookup))
            if "taxon_id" in o
            else o.loc[mask, key].map(lookup)
        )

    count = o.reindex(columns=COUNT_COLUMNS).copy()
    count["count_id"] = o.observation_id
    count["count_estimation"] = o.estimation
    count.loc[count.count_estimation.eq("x"), "count"] = pd.NA
    count["datetime"] = iso_time(pd.to_datetime(o.datetime, utc=True))
    if "datetime_interval" in o:
        count["datetime"] = o.datetime_interval.combine_first(count.datetime)
    # Preserve source associations; explicit dates prevent timing inheritance for fallbacks.
    linked = count.survey_id.isin(survey.survey_id)
    fallback = o.time_resolution.eq("day") & (
        o.source.eq("trektellen") | o["flags"].str.contains("time_outside_survey", na=False)
    )
    count.loc[~linked, "survey_id"] = pd.NA
    dated = (count.survey_id.isna() | fallback) & count.datetime.isna()
    count.loc[dated, "datetime"] = o.loc[dated, "date"].dt.strftime("%Y-%m-%d")
    prose = o.reindex(columns=["detail", "details", "comment", "list_comment", "remark"]).copy()
    for field in ("comment", "remark"):
        if field + "_residual" in o:
            prose.loc[o.source.eq("historical"), field] = o.loc[
                o.source.eq("historical"), field + "_residual"
            ]
    count["remark"] = combine_text(
        prose, ["detail", "details", "comment", "list_comment", "remark"]
    )
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
    reviewed_rows = o.loc[
        o.taxon_id.ne(o.avibase_id), ["source", "taxon_name_original", "taxon_id"]
    ].drop_duplicates()
    if len(reviewed_rows):
        reviewed_rows["avibase_id"] = reviewed_rows.taxon_id
        reviewed_rows[
            "mapping_note"
        ] = "Owner-reviewed historical source text; per-record mapping."
        mapping = pd.concat([mapping, reviewed_rows], ignore_index=True)
    resolved_taxa = taxonomy.taxa.set_index("avibase_id")
    for taxon_id, sources in mapping.loc[mapping.taxon_id.isin(count.taxon_id)].groupby(
        "taxon_id", sort=True
    ):
        resolved = resolved_taxa.reindex([sources.iloc[0].avibase_id]).iloc[0]
        source_fields = [
            "source",
            "taxon_name_original",
            "trektellen_species_id",
            "mapping_note",
            "review",
        ]
        source_data = sources.reindex(columns=source_fields)
        source_values = (
            source_data.astype(object).where(source_data.notna(), None).to_dict("records")
        )
        taxon_rows.append(
            {
                "taxon_id": taxon_id,
                **resolved.to_dict(),
                "trektellen_species_id": ",".join(
                    str(int(value))
                    for value in sorted(sources.trektellen_species_id.dropna().unique())
                )
                or pd.NA,
                "source_taxa": json.dumps(source_values, ensure_ascii=False),
            }
        )
    taxa = pd.DataFrame(taxon_rows)
    taxa["parent_taxon_id"] = taxa.taxon_id.map(taxonomy.parents)
    taxa = taxa.reindex(columns=TAXONOMY_COLUMNS)
    count.attrs["taxonomy_review"] = o.attrs.get("taxonomy_review", [])
    count.attrs["movement_review"] = o.attrs.get("movement_review", [])
    return (
        count[COUNT_COLUMNS].reset_index(drop=True),
        survey[SURVEY_COLUMNS].reset_index(drop=True),
        taxa,
    )


def local_dates(values):
    """Select collection days in the declared site timezone, including midnight crossings."""
    start = values.str.split("/").str[0]
    dates = start.str[:10].copy()
    timed = start.str.contains("T", na=False)
    # Many counts share a clock: convert each distinct value once.
    unique = pd.Series(start.loc[timed].unique())
    local = (
        pd.to_datetime(unique, utc=True, format="ISO8601")
        .dt.tz_convert(descriptor()["x-calendarTimezone"])
        .dt.strftime("%Y-%m-%d")
    )
    dates.loc[timed] = start.loc[timed].map(dict(zip(unique, local)))
    return dates


def daily_from_tables(count, survey):
    """Example derived view using only the two released tables; missing stays missing."""
    rows = count.merge(
        survey[["survey_id", "datetime"]],
        on="survey_id",
        how="left",
        suffixes=("", "_survey"),
        validate="many_to_one",
    )
    rows["date"] = local_dates(rows.datetime.fillna(rows.datetime_survey))
    for category, field in (("reverse", "count_reverse"), ("local", "count_local")):
        rows[field] = rows["count"].where(rows.count_category.eq(category))
    rows["count"] = rows["count"].where(rows.count_category.eq("normal"))
    return (
        rows.groupby(["date", "taxon_id"], sort=True)
        .agg(
            count=("count", lambda values: values.sum(min_count=1)),
            count_reverse=("count_reverse", lambda values: values.sum(min_count=1)),
            count_local=("count_local", lambda values: values.sum(min_count=1)),
            records=("count_id", "size"),
        )
        .reset_index()
    )


def parent_check(taxa, Check):
    """Every `parent_taxon_id` is a released taxon, and following parents never loops."""
    parent = taxa.set_index("taxon_id").parent_taxon_id.dropna()
    issues = [
        (c, p, "parent_not_released") for c, p in parent.items() if p not in set(taxa.taxon_id)
    ]
    for start in parent.index:
        seen, node = set(), start
        while node in parent.index and node not in seen:
            seen.add(node)
            node = parent[node]
        if node in seen:
            issues.append((start, node, "parent_cycle"))
    bad = pd.DataFrame(issues, columns=["taxon_id", "parent_taxon_id", "issue"])
    return Check(
        "Taxon parents are released and acyclic",
        "fail" if len(bad) else "pass",
        f"{len(bad)} taxa with a missing parent or a parent loop.",
        bad,
    )


def validate_tables(count, survey, taxa, ds, components=None, taxonomy_rules=None):
    """Return source-conservation results for the audit and publication gate."""
    from defile_dataset.checks import Check

    eligible = ds.observations.use_for_counts & ds.observations.taxon_kind.eq("bird")
    expected = ds.observations.loc[eligible].set_index("observation_id")
    movement_expected, _ = project_non_passage(expected)
    source_ids = count.source_count_id
    original = expected.reindex(source_ids)
    native = (
        original.survey_id.where(original.survey_id.isin(survey.survey_id))
        .reset_index(drop=True)
        .astype("string")
    )
    released = count.survey_id.reset_index(drop=True).astype("string")
    equal = released.eq(native).fillna(False) | (released.isna() & native.isna())
    native_links = pd.DataFrame(
        dict(count_id=count.count_id, released_survey_id=released, source_survey_id=native)
    ).loc[~equal]
    ids = pd.Index(count.count_id)
    expected_rows = category_counts(expected.reset_index(), components, taxonomy_rules)
    expected_ids = pd.Index(expected_rows.observation_id)
    missing = expected_ids.difference(ids)
    unexpected = ids.difference(expected_ids)
    duplicated = ids[ids.duplicated()].unique()
    bad = pd.DataFrame(
        [
            dict(count_id=value, issue=issue)
            for issue, values in [
                ("missing_eligible_row", missing),
                ("unexpected_row", unexpected),
                ("duplicated_row", duplicated),
            ]
            for value in values
        ],
        columns=["count_id", "issue"],
    )
    results = [
        Check(
            "Eligible count categories retained once",
            "fail" if len(bad) else "pass",
            f"{len(bad)} missing, unexpected or duplicate source IDs.",
            bad,
        )
    ]
    results.append(
        Check(
            "Survey associations preserved",
            "fail" if len(native_links) else "pass",
            f"{len(native_links)} survey associations differ from their available source survey.",
            native_links,
        )
    )
    for target, source in (("normal", "count"), ("reverse", "direction2"), ("local", "local")):
        exported = (
            count["count"]
            .where(count.count_category.eq(target))
            .groupby(source_ids)
            .sum(min_count=1)
            .reindex(expected.index)
            .reset_index(drop=True)
        )
        native = movement_expected[source].reset_index(drop=True)
        if target == "normal":
            native = native.mask(expected.estimation.eq("x").fillna(False).reset_index(drop=True))
        equal = exported.eq(native).fillna(False) | (exported.isna() & native.isna())
        bad = pd.DataFrame(
            dict(count_id=expected.index, released_value=exported, source_value=native)
        ).loc[~equal]
        results.append(
            Check(
                f"{target} values preserved",
                "fail" if len(bad) else "pass",
                f"{len(bad)} numerical values differ from the source after explicit non-passage projection. Presence-only main counts remain non-numerical.",
                bad,
            )
        )
    lineage = expected_rows.set_index("observation_id").reindex(count.count_id)
    equal = count.source_count_id.eq(
        lineage.source_count_id.reset_index(drop=True)
    ) & count.count_category.eq(lineage.count_category.reset_index(drop=True))
    bad = count.loc[~equal, ["count_id", "source_count_id", "count_category"]]
    results.append(
        Check(
            "Count category provenance preserved",
            "fail" if len(bad) else "pass",
            f"{len(bad)} rows have incorrect source identities or categories.",
            bad,
        )
    )
    if taxonomy_rules is not None:
        target = lineage.taxon_id.reset_index(drop=True).fillna(
            original.avibase_id.reset_index(drop=True)
        )
        bad = pd.DataFrame(
            dict(
                count_id=count.count_id, expected_taxon_id=target, released_taxon_id=count.taxon_id
            )
        ).loc[count.taxon_id.ne(target)]
        results.append(
            Check(
                "Reviewed taxonomy assignments preserved",
                "fail" if len(bad) else "pass",
                f"{len(bad)} taxa differ from the reviewed source-text projection.",
                bad,
            )
        )
    rows = count.merge(
        survey[["survey_id", "datetime"]], on="survey_id", how="left", suffixes=("", "_survey")
    )
    dates = local_dates(rows.datetime.fillna(rows.datetime_survey)).reset_index(drop=True)
    native = original.date.dt.strftime("%Y-%m-%d").reset_index(drop=True)
    bad = pd.DataFrame(dict(count_id=count.count_id, released_date=dates, source_date=native)).loc[
        dates.ne(native)
    ]
    results.append(
        Check(
            "Local collection dates preserved",
            "fail" if len(bad) else "pass",
            f"{len(bad)} local dates differ after timing inheritance.",
            bad,
        )
    )
    results.append(parent_check(taxa, Check))
    return results
