"""Compute the report's checks and final daily coverage; HTML only presents these results."""

import re

import pandas as pd

from defile_dataset.attributes import quantity_components
from defile_dataset.checks import Check
from defile_dataset.consolidate import local_dates
from defile_dataset.report_text import CHECK_TEXT
from defile_dataset.site import TIMEZONE


def daily_coverage(count, survey):
    """Summarize final records and retained survey intervals by local calendar day."""
    periods = []
    for row in survey.itertuples(index=False):
        start, end = [pd.Timestamp(value).tz_convert("UTC") for value in row.datetime.split("/")]
        first = start.tz_convert(TIMEZONE).normalize()
        last = (end - pd.Timedelta(nanoseconds=1)).tz_convert(TIMEZONE).normalize()
        for day in pd.date_range(first, last, freq="D"):
            periods.append(
                dict(
                    date=day.tz_localize(None),
                    survey_id=row.survey_id,
                    survey_complete=row.survey_complete,
                    weather_stop=row.weather_stop,
                    start=max(start, day),
                    end=min(end, day + pd.DateOffset(days=1)),
                )
            )
    periods = pd.DataFrame(
        periods, columns=["date", "survey_id", "survey_complete", "weather_stop", "start", "end"]
    )
    days = []
    for date, day in periods.groupby("date"):
        from defile_dataset.survey_review import observed_hours

        counted = day.survey_complete.fillna(True).astype(bool) & ~day.weather_stop.fillna(
            False
        ).astype(bool)
        days.append(
            dict(
                date=date,
                surveys=day.loc[counted, "survey_id"].nunique(),
                survey_hours=observed_hours(day),
                complete=int(counted.sum()),
                weather_stop=int(day.weather_stop.fillna(False).astype(bool).sum()),
                incomplete=int((~day.survey_complete.fillna(True).astype(bool)).sum()),
            )
        )
    rows = count.merge(
        survey[["survey_id", "datetime"]], on="survey_id", how="left", suffixes=("", "_survey")
    )
    rows["date"] = pd.to_datetime(local_dates(rows.datetime.fillna(rows.datetime_survey)))
    for category, field in (("reverse", "count_reverse"), ("local", "count_local")):
        rows[field] = rows["count"].where(rows.count_category.eq(category))
    rows["count"] = rows["count"].where(rows.count_category.eq("normal"))
    birds = (
        rows.groupby("date")
        .agg(
            entries=("count_id", "size"),
            count=("count", lambda values: values.sum(min_count=1)),
            count_reverse=("count_reverse", lambda values: values.sum(min_count=1)),
            count_local=("count_local", lambda values: values.sum(min_count=1)),
        )
        .reset_index()
    )
    result = pd.DataFrame(
        days, columns=["date", "surveys", "survey_hours", "complete", "weather_stop", "incomplete"]
    ).merge(birds, on="date", how="outer")
    for column in ("entries", "surveys", "complete", "weather_stop", "incomplete"):
        result[column] = result[column].fillna(0).astype(int)
    result["year"] = result.date.dt.year
    result["day_of_year"] = result.date.dt.dayofyear
    return result.sort_values("date").reset_index(drop=True)


def build_checks(ds, checks, validation, reviews, reconciliation):
    """One result per question: a status, relevant rows, explanation and edit location."""
    overlap_check = next(c for c in checks if c.name == "No overlapping surveys")
    result = [c for c in checks if c.name != "No overlapping surveys"]
    for check in result:
        check.key = re.sub(r"[^a-z0-9]+", "-", check.name.lower()).strip("-")
        check.file = "validation_findings.csv"
        check.action = (
            (
                "Inspect the original source record. Correct confirmed Trektellen errors and re-export; "
                "locate historical records by their source ID. Leave legitimate periods unchanged."
            )
            if not check.rows.empty
            else ""
        )
        if "tax" in check.name.lower() or "Avibase" in check.name:
            check.action = (
                "Review taxonomy/source_taxa.csv against the maintained checklists."
                if not check.rows.empty
                else ""
            )
        if check.name == "Surveys into the night":
            check.columns = (
                "date",
                "survey_id",
                "source",
                "start",
                "end",
                "sunrise",
                "sunset",
                "civil_dawn",
                "civil_dusk",
                "minutes_before_sunrise",
                "minutes_after_sunset",
                "night_minutes",
                "duration_hours",
            )
            check.filter_column = "night_minutes"
            check.filter_threshold = 30
        elif check.name == "Long surveys":
            check.columns = (
                "date",
                "survey_id",
                "source",
                "start",
                "end",
                "duration_hours",
                "night_minutes",
            )
            check.filter_column = "duration_hours"
            check.filter_threshold = 15
    result.insert(
        0,
        Check(
            "Released CSV requirements",
            "pass" if validation["valid"] else "fail",
            "Field types, constraints, primary/foreign keys and conditional project rules.",
            pd.DataFrame(validation.get("x-projectErrors", [])),
            file="datapackage_validation.json",
            key="csv-requirements",
        ),
    )
    # These are source review findings, not failed released-table constraints.
    for issue, title, action in [
        (
            "Timestamp outside period",
            "Entry times outside their source period",
            "Check entry times and period bounds in Trektellen. Entries remain at day resolution until corrected.",
        ),
        (
            "Entry without time",
            "Entries missing a time",
            "Add a time only when the original evidence supports it. Otherwise keep the valid day-level record.",
        ),
    ]:
        rows = ds.issues.loc[ds.issues.issue.eq(issue)]
        result.append(
            Check(
                title,
                "warn" if len(rows) else "pass",
                f"{len(rows):,} affected survey findings; only affected entries are described in each row.",
                rows,
                action=action,
                file="entry_issues.csv",
                columns=(
                    "date",
                    "survey_id",
                    "start",
                    "end",
                    "outside_minutes",
                    "detail",
                    "entries",
                    "birds",
                )
                if issue == "Timestamp outside period"
                else ("date", "survey_id", "start", "end", "detail", "entries", "birds"),
                key=re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-"),
                filter_column="outside_minutes" if issue == "Timestamp outside period" else "",
                filter_threshold=10 if issue == "Timestamp outside period" else 0,
            )
        )
    excluded = ds.surveys.loc[ds.surveys.duplicate_of.notna()].copy()
    original = ds.surveys.set_index("survey_id")
    excluded["kept_start"] = excluded.duplicate_of.map(original.start)
    excluded["kept_end"] = excluded.duplicate_of.map(original.end)
    excluded["overlap_minutes"] = (
        (
            excluded[["end", "kept_end"]].min(axis=1)
            - excluded[["start", "kept_start"]].max(axis=1)
        ).dt.total_seconds()
        / 60
    ).clip(lower=0)
    totals = ds.observations.groupby("survey_id")["count"].agg(
        excluded_records="size", excluded_source_count="sum"
    )
    excluded = excluded.join(totals, on="survey_id")
    excluded["assessment"] = "later_period_excluded"
    if not overlap_check.rows.empty:
        excluded = pd.concat(
            [excluded, overlap_check.rows.assign(assessment="unresolved_retained_overlap")],
            ignore_index=True,
        )
    result.append(
        Check(
            "Overlapping surveys",
            "fail" if overlap_check.status == "fail" else "warn" if len(excluded) else "pass",
            "Retained periods must not overlap. Resolved source overlaps are shown for review: the earlier period is kept and the later period excluded in full. Compare both periods and the excluded source total.",
            excluded,
            action="Inspect both source periods using their native IDs. Correct duplicate or mis-entered headers in Trektellen and re-export when supported.",
            file="overlap_review.csv",
            columns=(
                "assessment",
                "date",
                "survey_id",
                "start",
                "end",
                "duplicate_of",
                "kept_start",
                "kept_end",
                "overlap_minutes",
                "excluded_records",
                "excluded_source_count",
            ),
            key="source-overlaps",
        )
    )
    attributes = reviews["attributes"].copy()
    attributes["taxon_name_original"] = attributes.observation_id.map(
        ds.observations.set_index("observation_id").taxon_name_original
    )
    for state, title, action in [
        (
            "quantity_mismatch",
            "Detail quantities exceed the source count",
            "Check the workbook sheet/row and each detail component. Do not replace the source total with a conflicting detail sum.",
        ),
        (
            "unparsed",
            "Historical details with an unrecognised format",
            "Review the original detail and correct the source format only when justified.",
        ),
        (
            "unassigned",
            "Historical attributes left unassigned",
            "Review config/attributes/historical_attributes.csv. Unknown or ambiguous descriptions can remain unassigned.",
        ),
        (
            "partial",
            "Historical attributes only partly assigned",
            "Review the supported shared attributes and original group description; do not infer unsupported age or sex.",
        ),
    ]:
        rows = attributes.loc[attributes.status.eq(state)]
        if state == "quantity_mismatch":
            rows = (
                reviews["quantity_components"]
                .loc[reviews["quantity_components"].status.eq("quantity_mismatch")]
                .copy()
            )
            rows["taxon_name_original"] = rows.observation_id.map(
                ds.observations.set_index("observation_id").taxon_name_original
            )
        result.append(
            Check(
                title,
                "warn" if len(rows) else "pass",
                f"{len(rows):,} review rows.",
                rows,
                action=action,
                file="attribute_quantity_review.csv"
                if state == "quantity_mismatch"
                else "attribute_review.csv",
                key="attributes-" + state,
            )
        )
    status = reviews["status"]
    for issue in sorted(status.issue.unique()):
        rows = status.loc[status.issue.eq(issue)].copy()
        columns = ("date", "survey_id", "issue", "detail", "weather", "remarks")
        result.append(
            Check(
                "Survey status: " + issue.replace("_", " "),
                "warn",
                f"{len(rows):,} source surveys to review.",
                rows,
                action="Read the source remarks and weather. Historical header decisions are in count_2021.xlsx (Pression observation); added historical intervals are reviewed in config/audit-settings/historical-gap-breaks.csv. Trektellen decisions are in config/survey-status/trektellen-survey-status.csv, or correct source tags and re-export.",
                file="survey_status_review.csv",
                columns=columns,
                key="survey-status-" + issue,
            )
        )
    unresolved = reviews["coverage"].loc[reviews["coverage"].assessment.eq("unresolved")]
    result.append(
        Check(
            "Missing or short coverage within reported seasons",
            "warn" if len(unresolved) else "pass",
            "Only unresolved dates are shown. Season bounds and short-day thresholds come from config/audit-settings/report-season-windows.csv; absence alone does not establish a closure.",
            unresolved,
            action="Check original records and report evidence. Add supported status decisions or notes in config/audit-settings/interruption-review-notes.csv.",
            file="interruption_review.csv",
            columns=(
                "date",
                "native_survey_ids",
                "native_hours",
                "bird_rows",
                "bird_total",
                "no_species_marker",
                "note",
            ),
            key="season-coverage",
        )
    )
    balanced = reconciliation.source_count.eq(
        reconciliation[
            [
                "retained_count",
                "excluded_overlap_count",
                "excluded_non_bird_count",
                "excluded_no_species_count",
            ]
        ].sum(axis=1)
    )
    result.append(
        Check(
            "Counts accounted for after selection",
            "pass" if balanced.all() else "fail",
            "Source count = retained bird count + mutually exclusive overlap, non-bird and no-species exclusions. This verifies accounting, separately from reviewing overlaps.",
            reconciliation,
            file="reconciliation.csv",
            key="count-accounting",
        )
    )
    for check in result:
        if check.key in CHECK_TEXT:
            check.name, _, check.detail, _ = CHECK_TEXT[check.key]
        if check.key.startswith("attributes-"):
            check.group = "Historical records"
        elif check.key == "season-coverage":
            check.group = "Coverage and published totals"
        elif check.key.startswith("survey-status-") or check.key in (
            "surveys-into-the-night",
            "long-surveys",
            "source-overlaps",
            "positive-durations",
        ):
            check.group = "Surveys"
        elif check.key in (
            "entries-missing-a-time",
            "entry-times-outside-their-source-period",
            "timestamps-inside-their-survey",
        ):
            check.group = "Counts and data integrity"
    return sorted(result, key=lambda check: {"fail": 0, "warn": 1, "pass": 2}[check.status])


def summarize(checks):
    """Save exactly the result list that the report renders."""
    return dict(
        build_status="blocked" if any(c.status == "fail" for c in checks) else "passed",
        tests=[
            dict(
                id=c.key,
                name=c.name,
                status=c.status,
                detail=c.detail,
                rows=len(c.rows),
                action=c.action,
                file=c.file,
                group=c.group,
                filter_column=c.filter_column,
                filter_threshold=c.filter_threshold,
            )
            for c in checks
        ],
    )
