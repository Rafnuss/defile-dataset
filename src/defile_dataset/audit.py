"""Compute the report's checks and final daily coverage; HTML only presents these results."""

import re

import numpy as np
import pandas as pd

from defile_dataset.attributes import quantity_components
from defile_dataset.checks import Check
from defile_dataset.consolidate import local_dates
from defile_dataset.report_text import CHECK_TEXT
from defile_dataset.site import TIMEZONE

OUTLIER_THRESHOLD = 3
OUTLIER_MIN_DAYS = 20
OUTLIER_WINDOW_DAYS = 15


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


def outlier_comments(count, survey):
    """Keep count remarks and linked survey context separate, labelled with released IDs."""
    rows = count.reindex(columns=["count_id", "survey_id", "remark"]).merge(
        survey.reindex(columns=["survey_id", "survey_comment", "remark"]),
        on="survey_id", how="left", suffixes=("", "_survey"),
    )
    for field, source, identifier in (
        ("count_remarks", "remark", "count_id"),
        ("survey_comments", "survey_comment", "survey_id"),
        ("survey_remarks", "remark_survey", "survey_id"),
    ):
        text = rows[source].fillna("")
        rows[field] = (rows[identifier].fillna("") + ": " + text).where(text.ne(""), "")
    return rows[["count_id", "count_remarks", "survey_comments", "survey_remarks"]]


def count_outliers(count, survey, taxonomy, coverage):
    """Rank positive totals/rates relative to the seasonal upper tail of each taxon."""
    rows = count.merge(
        survey[["survey_id", "datetime"]], on="survey_id", how="left", suffixes=("", "_survey")
    )
    rows["date"] = pd.to_datetime(local_dates(rows.datetime.fillna(rows.datetime_survey)))
    # Presence-only rows contribute neither a numerical zero nor rate eligibility.
    rows = rows.loc[rows["count"].notna()].copy()
    rows["linked"] = rows.datetime_survey.notna()
    rows = rows.merge(outlier_comments(count, survey), on="count_id", how="left")
    daily = (
        rows.groupby(["date", "taxon_id", "count_category"])
        .agg(
            daily_count=("count", "sum"),
            linked=("linked", "all"),
            survey_ids=("survey_id", lambda values: "|".join(sorted(values.dropna().unique()))),
            count_ids=("count_id", lambda values: "|".join(sorted(values))),
            count_remarks=("count_remarks", lambda values: "\n".join(values.loc[values.ne("")].unique())),
            survey_comments=("survey_comments", lambda values: "\n".join(values.loc[values.ne("")].unique())),
            survey_remarks=("survey_remarks", lambda values: "\n".join(values.loc[values.ne("")].unique())),
        )
        .reset_index()
    )
    daily = daily.merge(coverage[["date", "survey_hours"]], on="date", how="left")
    daily["count_rate"] = daily.daily_count.astype(float).div(
        daily.survey_hours.where(daily.linked & daily.survey_hours.gt(0))
    )
    daily = daily.merge(taxonomy[["taxon_id", "english_name"]], on="taxon_id", how="left")
    # A fixed leap year aligns month/day across years, including February 29.
    daily["season_day"] = pd.to_datetime("2000-" + daily.date.dt.strftime("%m-%d")).dt.dayofyear
    result = []
    for metric in ("daily_count", "count_rate"):
        scored = daily.copy()
        scored["metric"] = metric
        scored["value"] = scored[metric].astype(float)
        scored["reference_days"] = 0
        for field in ("reference_median", "reference_p95", "reference_max", "outlier_score"):
            scored[field] = np.nan
        for _, group in scored.groupby(["taxon_id", "count_category"]):
            positive = group.loc[group.value.gt(0)]
            values = positive.value.to_numpy()
            days = positive.season_day.to_numpy()
            indices = positive.index.to_numpy()
            for row in positive.itertuples():
                distance = np.abs(days - row.season_day)
                nearby = np.minimum(distance, 366 - distance) <= OUTLIER_WINDOW_DAYS
                reference = values[nearby & (indices != row.Index)]
                scored.loc[row.Index, "reference_days"] = len(reference)
                if len(reference) < OUTLIER_MIN_DAYS:
                    continue
                median, p95 = np.quantile(reference, [0.5, 0.95])
                scored.loc[
                    row.Index,
                    ["reference_median", "reference_p95", "reference_max", "outlier_score"],
                ] = [
                    median,
                    p95,
                    reference.max(),
                    row.value / reference.max(),
                ]
        scored["flagged"] = scored.outlier_score.gt(OUTLIER_THRESHOLD)
        result.append(scored)
    return (
        pd.concat(result, ignore_index=True)
        .sort_values(
            ["outlier_score", "date", "taxon_id", "count_category", "metric"],
            ascending=[False, True, True, True, True],
            na_position="last",
        )
        .drop(columns="linked")
        .reset_index(drop=True)
    )


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
            check.filter_threshold = 16
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
                "info" if issue == "incomplete_survey" else "warn",
                f"{len(rows):,} source surveys to review.",
                rows,
                action="Read the source remarks and weather. Historical header decisions are in count_2021.xlsx (Pression observation); added historical intervals are reviewed in config/audit-settings/historical-gap-breaks.csv. Trektellen decisions are in config/survey-status/trektellen-survey-status.csv, or correct source tags and re-export.",
                file="survey_status_review.csv",
                columns=columns,
                key="survey-status-" + issue,
            )
        )
    result.append(
        Check(
            "Coverage context within reported seasons",
            "info",
            "Missing dates, short days and documented statuses are coverage context, not inconsistencies.",
            reviews["coverage"],
            file="interruption_review.csv",
            columns=(
                "date",
                "native_survey_ids",
                "native_hours",
                "complete",
                "incomplete",
                "weather_stop",
                "bird_rows",
                "bird_total",
                "no_species_marker",
                "assessment",
                "note",
            ),
            key="season-coverage",
        )
    )
    for metric, key in (
        ("daily_count", "daily-count-outliers"),
        ("count_rate", "count-rate-outliers"),
    ):
        rows = reviews["count_outliers"]
        rows = rows.loc[rows.metric.eq(metric) & rows.flagged]
        result.append(
            Check(
                CHECK_TEXT[key][0],
                "warn" if len(rows) else "pass",
                CHECK_TEXT[key][2],
                rows,
                action="Review the original counts and survey effort. Keep genuine migration peaks; correct only confirmed source errors.",
                file="count_outliers.csv",
                key=key,
                columns=(
                    "outlier_score",
                    "date",
                    "english_name",
                    "taxon_id",
                    "count_category",
                    "daily_count",
                    "survey_hours",
                    "count_rate",
                    "reference_median",
                    "reference_p95",
                    "reference_max",
                    "reference_days",
                    "count_remarks",
                    "survey_comments",
                    "survey_remarks",
                    "survey_ids",
                    "count_ids",
                ),
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
        if check.status == "info":
            check.action = ""
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
    return sorted(
        result, key=lambda check: {"fail": 0, "warn": 1, "pass": 2, "info": 3}[check.status]
    )


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
