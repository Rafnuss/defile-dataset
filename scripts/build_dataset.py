#!/usr/bin/env python3
"""Build five scientific tables, focused audits and internal processing tables.

Usage:
    uv run python scripts/build_dataset.py
    uv run python scripts/build_dataset.py --out /some/dir
    uv run python scripts/build_dataset.py --online-report-links
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from defile_dataset import read  # noqa: E402
from defile_dataset.attributes import historical_attributes  # noqa: E402
from defile_dataset.audit import (  # noqa: E402
    build_checks,
    daily_coverage,
    quantity_components,
    summarize,
)
from defile_dataset.audit_plots import coverage_assets
from defile_dataset.build import build, daily_counts  # noqa: E402
from defile_dataset.checks import run_checks  # noqa: E402
from defile_dataset.consolidate import (  # noqa: E402
    consolidate,
    daily_from_tables,
    validate_tables,
)
from defile_dataset.identities import readable_ids
from defile_dataset.package import descriptor, generate_docs, validate_package  # noqa: E402
from defile_dataset.reconcile import compare_report_totals  # noqa: E402
from defile_dataset.remark_text import convert_remark_text
from defile_dataset.report import render  # noqa: E402
from defile_dataset.source_text import CLOCK_TEXT
from defile_dataset.survey_review import (
    empty_survey_review,
    integrate_historical_gaps,
    integrate_interruptions,
    interruption_review,
    validate_historical_gaps,
)
from defile_dataset.survey_status import classify_trektellen, read_reviewed_status, release_status
from defile_dataset.taxonomy import (  # noqa: E402
    AVILIST_FILE,
    EBIRD_FILE,
    SOURCE_TAXA_FILE,
    Taxonomy,
)
from defile_dataset.taxonomy_tree import tree_section  # noqa: E402
from defile_dataset.timing_review import reviewed_entry_times

RAW_DIR = os.path.join(ROOT, "raw")


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _git(*args) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _write_csv(df, path: str) -> None:
    tmp = path + ".tmp"
    df.to_csv(tmp, index=False, encoding="utf-8-sig")
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    ap.add_argument("--interim", default=os.path.join(ROOT, "interim"))
    ap.add_argument(
        "--online-report-links",
        action="store_true",
        help="Link annual-report PDFs to their source URLs for a hosted audit",
    )
    args = ap.parse_args(argv)

    # Read and standardize sources -----------------------------------------------

    years = read.trektellen_years(RAW_DIR)
    print(f"Reading {read.HISTORICAL_FILE} and Trektellen {years} ...")
    hist = read.read_historical(RAW_DIR)
    effort = read.read_effort(RAW_DIR)
    sightings, counts = read.read_trektellen(RAW_DIR)
    taxonomy_rules = pd.read_csv(
        os.path.join(ROOT, "config/taxonomy/historical_text_mappings.csv"), keep_default_na=False
    )
    taxonomy = Taxonomy.load(ROOT, taxonomy_rules)

    attribute_crosswalk = pd.read_csv(
        os.path.join(ROOT, "config/attributes/historical_attributes.csv"), dtype=str
    )
    attribute_values, attribute_audit = historical_attributes(hist, attribute_crosswalk)
    hist = hist.join(attribute_values)
    attribute_components = quantity_components(attribute_audit)
    print(f"  Historical attribute review: {attribute_audit['status'].value_counts().to_dict()}")

    # Map records, classify surveys and consolidate -----------------------------
    ds = build(hist, effort, sightings, counts, taxonomy)
    timing_decisions = pd.read_csv(
        os.path.join(ROOT, "config/timing/reviewed-entry-times.csv"), keep_default_na=False
    )
    ds.observations, timing_audit = reviewed_entry_times(
        ds.observations, ds.surveys, timing_decisions
    )
    ds.surveys, status_intervals, status_review = classify_trektellen(
        ds.surveys, ds.observations, read_reviewed_status(ROOT)
    )
    count_table, survey_table, taxon_table = consolidate(ds, taxonomy, attribute_components)
    taxonomy_audit = pd.DataFrame(count_table.attrs.pop("taxonomy_review"))
    movement_audit = pd.DataFrame(count_table.attrs.pop("movement_review"))
    count_table, text_changes = convert_remark_text(count_table, survey_table)
    conservation = validate_tables(
        count_table, survey_table, taxon_table, ds, attribute_components, taxonomy_rules
    )
    text_table = pd.read_csv(
        os.path.join(ROOT, "raw/reports/report_text.csv"), keep_default_na=False
    )
    paper_text_table = pd.read_csv(
        os.path.join(ROOT, "raw/reports/paper_text.csv"), keep_default_na=False
    )
    survey_table, count_table, interruption_table = integrate_interruptions(
        survey_table, count_table, ROOT, status_intervals
    )
    historical_breaks = pd.read_csv(
        os.path.join(ROOT, "config/audit-settings/historical-gap-breaks.csv")
    )
    survey_table, historical_gaps = integrate_historical_gaps(
        survey_table, hist, historical_breaks
    )
    interruption_audit = interruption_review(
        survey_table, ds.observations, ROOT, interruption_table
    )
    count_ids = count_table.count_id.copy()
    count_table, survey_table, interruption_table = readable_ids(
        count_table, survey_table, ds.observations, interruption_table, taxon_table
    )
    taxonomy_audit["count_id"] = (taxonomy_audit.observation_id + "-normal").map(
        dict(zip(count_ids, count_table.count_id))
    )
    movement_audit["count_id_local"] = (movement_audit.observation_id + "-local").map(
        dict(zip(count_ids, count_table.count_id))
    )
    text_changes["count_id"] = text_changes.count_id.map(
        dict(zip(count_ids, count_table.count_id))
    )
    historical_gaps["survey_id"] = historical_gaps.source_survey_id.map(
        survey_table.set_index("source_survey_id").survey_id
    )
    empty_surveys = empty_survey_review(
        survey_table, count_table, ds.observations, historical_gaps
    )
    status_review["source_survey_id"] = status_review.survey_id
    status_review["survey_id"] = status_review.source_survey_id.map(
        survey_table.set_index("source_survey_id").survey_id
    ).fillna(status_review.source_survey_id)
    released_ids = pd.Series(count_table.count_id.values, index=count_ids)
    checks = (
        conservation
        + run_checks(ds, taxonomy)
        + validate_historical_gaps(survey_table, count_table, historical_gaps)
    )
    print(f"  {ds.issues['survey_id'].nunique()} survey intervals with audit findings.")

    # Stage generated products; the previous build stays available on failure -----
    stage = args.out + ".building"
    if os.path.isdir(stage):
        shutil.rmtree(stage)
    dataset_dir, audit_dir, gbif_dir = [
        os.path.join(stage, name) for name in ("dataset", "audit", "gbif")
    ]
    processed_dir, derived_dir, diagnostic_dir = [
        os.path.join(stage, "interim", name) for name in ("processed", "derived", "diagnostics")
    ]
    for folder in (dataset_dir, audit_dir, gbif_dir, processed_dir, derived_dir, diagnostic_dir):
        os.makedirs(folder, exist_ok=True)
    for name, data in (
        ("count", count_table),
        ("survey", release_status(survey_table)),
        ("taxonomy", taxon_table),
        ("report_text", text_table),
        ("paper_text", paper_text_table),
    ):
        _write_csv(data, os.path.join(dataset_dir, name + ".csv"))
    generate_docs(dataset_dir, repository_docs=False)
    shutil.copyfile(
        os.path.join(ROOT, "docs/templates/gbif-readme.md"), os.path.join(gbif_dir, "README.md")
    )
    shutil.copyfile(os.path.join(ROOT, "docs/audit.md"), os.path.join(audit_dir, "README.md"))
    validation = validate_package(os.path.join(dataset_dir, "datapackage.json"))
    with open(os.path.join(audit_dir, "datapackage_validation.json"), "w") as f:
        json.dump(validation, f, ensure_ascii=False, indent=2)
    print(f"  Released CSV validation: {'pass' if validation['valid'] else 'fail'}.")
    _write_csv(interruption_audit, os.path.join(audit_dir, "interruption_review.csv"))
    _write_csv(historical_gaps, os.path.join(audit_dir, "historical_effort_gaps.csv"))
    _write_csv(empty_surveys, os.path.join(audit_dir, "empty_survey_review.csv"))
    _write_csv(status_review, os.path.join(audit_dir, "survey_status_review.csv"))
    _write_csv(
        attribute_audit.drop(columns="components"),
        os.path.join(diagnostic_dir, "historical_attributes.csv"),
    )
    attribute_components["released_count_id"] += "-normal"
    attribute_components["released_count_id"] = attribute_components.released_count_id.map(
        released_ids
    )
    _write_csv(attribute_components, os.path.join(diagnostic_dir, "historical_components.csv"))
    _write_csv(
        attribute_audit.loc[attribute_audit.status.ne("mapped")].drop(columns="components"),
        os.path.join(audit_dir, "attribute_review.csv"),
    )
    _write_csv(ds.surveys, os.path.join(processed_dir, "surveys.csv"))
    _write_csv(ds.observations, os.path.join(processed_dir, "observations.csv"))
    _write_csv(
        ds.surveys.loc[ds.surveys.duplicate_of.notna()],
        os.path.join(audit_dir, "excluded_surveys.csv"),
    )
    selection = ds.observations.copy()
    selection["exclusion_reason"] = ""
    selection.loc[~selection.use_for_counts, "exclusion_reason"] = "overlapping_period"
    selection.loc[selection.taxon_kind.eq("non_bird"), "exclusion_reason"] = "non_bird"
    selection.loc[selection.taxon_kind.eq("no_species"), "exclusion_reason"] = "no_species_entry"
    _write_csv(
        selection.loc[selection.exclusion_reason.ne("")],
        os.path.join(audit_dir, "excluded_counts.csv"),
    )
    _write_csv(ds.issues, os.path.join(audit_dir, "entry_issues.csv"))
    _write_csv(timing_audit, os.path.join(audit_dir, "entry_time_corrections.csv"))
    clock_text = (
        ds.observations.reindex(columns=["comment", "remark"])
        .fillna("")
        .apply(lambda values: values.str.contains(CLOCK_TEXT, regex=True))
        .any(axis=1)
    )
    text_review = ds.observations.loc[
        clock_text,
        [
            "observation_id",
            "date",
            "source",
            "taxon_name_original",
            "count",
            "datetime_original",
            "timing_source",
            "time_text_status",
            "comment",
            "remark",
        ],
    ].copy()
    reviewed_counts = count_table.loc[
        count_table.source_count_id.isin(text_review.observation_id)
    ].groupby("source_count_id")
    text_review["released_datetime"] = text_review.observation_id.map(
        reviewed_counts.datetime.agg(lambda values: " | ".join(dict.fromkeys(values.dropna())))
    )
    text_review["remaining_text"] = text_review.observation_id.map(
        reviewed_counts.remark.agg(lambda values: "\n\n".join(dict.fromkeys(values.dropna())))
    )
    text_review["released_count_ids"] = text_review.observation_id.map(
        reviewed_counts.count_id.agg(" | ".join)
    )
    text_review["released_rows"] = text_review.observation_id.map(reviewed_counts.size())
    _write_csv(text_review, os.path.join(audit_dir, "count_text_review.csv"))
    _write_csv(text_changes, os.path.join(audit_dir, "count_text_changes.csv"))
    _write_csv(taxonomy_audit, os.path.join(audit_dir, "historical_taxonomy_review.csv"))
    _write_csv(movement_audit, os.path.join(audit_dir, "movement_text_review.csv"))
    daily = daily_from_tables(count_table, survey_table)
    _write_csv(daily, os.path.join(derived_dir, "daily_counts.csv"))
    _write_csv(daily_counts(ds), os.path.join(diagnostic_dir, "daily_source_resolution.csv"))
    reconciliation = (
        selection.assign(
            year=selection["date"].dt.year,
            retained_count=selection["count"].where(selection.exclusion_reason.eq(""), 0),
            excluded_overlap_count=selection["count"].where(
                selection.exclusion_reason.eq("overlapping_period"), 0
            ),
            excluded_non_bird_count=selection["count"].where(
                selection.exclusion_reason.eq("non_bird"), 0
            ),
            excluded_no_species_count=selection["count"].where(
                selection.exclusion_reason.eq("no_species_entry"), 0
            ),
        )
        .groupby(["source", "year"])
        .agg(
            source_count=("count", "sum"),
            retained_count=("retained_count", "sum"),
            excluded_overlap_count=("excluded_overlap_count", "sum"),
            excluded_non_bird_count=("excluded_non_bird_count", "sum"),
            excluded_no_species_count=("excluded_no_species_count", "sum"),
        )
        .reset_index()
    )
    _write_csv(reconciliation, os.path.join(audit_dir, "reconciliation.csv"))

    # Compare reference totals without forcing agreement or assuming one report scope.
    reference = pd.read_csv(
        os.path.join(ROOT, "raw/reports/annual-totals.csv"), dtype={"count": "Int64"}
    )
    report_taxa = pd.read_csv(os.path.join(ROOT, "taxonomy/report_taxa.csv"))
    comparison = compare_report_totals(ds.observations, reference, report_taxa)
    pages = pd.read_csv(
        os.path.join(ROOT, "raw/reports/annual-total-pages.csv"), dtype={"pdf_page": "Int64"}
    )
    reports = pd.read_csv(os.path.join(ROOT, "raw/reports/sources.csv"))
    reports["report_pdf"] = reports.url if args.online_report_links else "../../" + reports.path
    comparison = comparison.merge(pages, on=["year", "species"], how="left").merge(
        reports[["year", "report_pdf"]], on="year", how="left"
    )
    _write_csv(comparison, os.path.join(audit_dir, "report_reconciliation.csv"))
    report_taxa = report_taxa.assign(
        taxon_name_original=report_taxa.dataset_taxa.str.split("|")
    ).explode("taxon_name_original")
    report_taxa = report_taxa.merge(
        taxonomy.source_taxa,
        left_on=["dataset_source", "taxon_name_original"],
        right_on=["source", "taxon_name_original"],
    )
    report_taxa["taxonomy_order"] = report_taxa.avibase_id.map(
        pd.Series(range(len(taxonomy.ebird)), index=taxonomy.ebird.index)
    )
    taxonomy_order = (
        report_taxa.groupby("species").taxonomy_order.min().dropna().astype(int).to_dict()
    )

    reviews = {
        "entries": ds.issues,
        "status": status_review,
        "attributes": attribute_audit.loc[attribute_audit.status.ne("mapped")].drop(
            columns="components"
        ),
        "coverage": interruption_audit,
    }
    reviews["quantity_components"] = attribute_components.loc[
        attribute_components.status.ne("mapped")
    ]
    checks = build_checks(ds, checks, validation, reviews, reconciliation)
    for c in checks:
        print(f"  [{c.status:4s}] {c.name}: {c.detail}")
    coverage = daily_coverage(count_table, survey_table, interruption_table)
    coverage_assets(os.path.join(audit_dir, "coverage"))
    coverage_season = pd.read_csv("config/audit-settings/coverage-season.csv").iloc[0].to_dict()
    _write_csv(
        reviews["quantity_components"], os.path.join(audit_dir, "attribute_quantity_review.csv")
    )
    _write_csv(
        next(c.rows for c in checks if c.key == "source-overlaps"),
        os.path.join(audit_dir, "overlap_review.csv"),
    )
    _write_csv(coverage, os.path.join(audit_dir, "daily_coverage.csv"))
    findings = (
        pd.concat(
            [
                c.rows.assign(test=c.name, status=c.status)
                for c in checks
                if c.file == "validation_findings.csv" and not c.rows.empty
            ],
            ignore_index=True,
        )
        if any(c.file == "validation_findings.csv" and not c.rows.empty for c in checks)
        else pd.DataFrame(columns=["test", "status"])
    )
    _write_csv(findings, os.path.join(audit_dir, "validation_findings.csv"))
    audit = summarize(checks)
    audit["summaries"] = [
        dict(name="Coverage by day and year", file="daily_coverage.csv", rows=len(coverage)),
        dict(
            name="Reviewed entry time corrections",
            file="entry_time_corrections.csv",
            rows=len(timing_audit),
        ),
        dict(
            name="Published annual totals", file="report_reconciliation.csv", rows=len(comparison)
        ),
    ]
    with open(os.path.join(audit_dir, "audit.json"), "w") as f:
        json.dump(audit, f, ensure_ascii=False, indent=2)

    raw_files = [os.path.join("raw", read.HISTORICAL_FILE)] + [
        os.path.join(
            "raw", read.TREKTELLEN_DIR, pattern.format(site=read.TREKTELLEN_SITE_ID, year=y)
        )
        for y in years
        for pattern in (read.TREKTELLEN_DATA_PATTERN, read.TREKTELLEN_HEADER_PATTERN)
    ]
    table_files = [
        "dataset/count.csv",
        "dataset/survey.csv",
        "dataset/taxonomy.csv",
        "dataset/report_text.csv",
        "dataset/paper_text.csv",
        "dataset/datapackage.json",
        "dataset/README.md",
        "gbif/README.md",
        "audit/README.md",
        "audit/interruption_review.csv",
        "audit/survey_status_review.csv",
        "audit/attribute_review.csv",
        "audit/entry_issues.csv",
        "audit/reconciliation.csv",
        "audit/report_reconciliation.csv",
        "audit/excluded_counts.csv",
        "audit/excluded_surveys.csv",
        "audit/datapackage_validation.json",
        "audit/audit.json",
        "audit/attribute_quantity_review.csv",
        "audit/overlap_review.csv",
        "audit/daily_coverage.csv",
        "audit/validation_findings.csv",
        "audit/historical_effort_gaps.csv",
        "audit/entry_time_corrections.csv",
        "audit/empty_survey_review.csv",
        "audit/count_text_review.csv",
        "audit/count_text_changes.csv",
        "audit/historical_taxonomy_review.csv",
        "audit/movement_text_review.csv",
    ]
    table_files += [
        os.path.relpath(os.path.join(folder, name), stage)
        for folder, _, names in os.walk(os.path.join(audit_dir, "coverage"))
        for name in sorted(names)
    ]
    interim_files = [
        "processed/surveys.csv",
        "processed/observations.csv",
        "derived/daily_counts.csv",
        "diagnostics/daily_source_resolution.csv",
        "diagnostics/historical_attributes.csv",
        "diagnostics/historical_components.csv",
    ]
    dirty = bool(
        _git("status", "--porcelain", "--", "raw", "taxonomy", "src", "scripts", "config", "docs")
    )
    metadata = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git("rev-parse", "HEAD") + (" (uncommitted changes)" if dirty else ""),
        "surveys": len(ds.surveys),
        "observations": len(ds.observations),
        "birds": int(ds.observations.loc[ds.observations.taxon_kind.eq("bird"), "count"].sum()),
        "source_count_sum": int(ds.observations["count"].sum()),
        "excluded_non_bird_rows": int(selection.exclusion_reason.eq("non_bird").sum()),
        "excluded_non_bird_count_sum": int(
            selection.loc[selection.exclusion_reason.eq("non_bird"), "count"].sum()
        ),
        "no_species_entries": int(selection.exclusion_reason.eq("no_species_entry").sum()),
        "retained_count_sum": int(daily["count"].sum()),
        "excluded_overlap_count_sum": int(
            ds.observations.loc[~ds.observations["use_for_counts"], "count"].sum()
        ),
        "processing_policy": "daily-fallback-first-overlap-v1",
        "consolidated_schema": descriptor()["x-schemaVersion"],
        "consolidated_counts": len(count_table),
        "consolidated_surveys": len(survey_table),
        "consolidated_taxa": len(taxon_table),
        "report_text_accounts": len(text_table),
        "paper_text_accounts": len(paper_text_table),
        "incomplete_surveys": int((~survey_table.survey_complete).sum()),
        "weather_stop_surveys": int(survey_table.weather_stop.sum()),
        "added_curated_periods": int(survey_table.recording_era.eq("curated").sum()),
        "historical_effort_gap_rows": int(historical_gaps.status.eq("added").sum()),
        "historical_effort_gap_hours": float(
            historical_gaps.loc[historical_gaps.status.eq("added"), "hours"].sum()
        ),
        "historical_cut_hours": float(
            historical_gaps.loc[historical_gaps.status.eq("cut"), "hours"].sum()
        ),
        "datapackage_validation": "pass",
        "attribute_crosswalk": "historical-attributes-age-bound-v3",
        "attribute_split_policy": "historical-normal-subgroups-v3",
        "count_category_policy": "normal-reverse-local-marker-overrides-v3",
        "non_passage_reclassified_birds": int(
            movement_audit.loc[movement_audit.status.eq("moved_to_local"), "count"].sum()
        ),
        "local_marker_reclassified_birds": int(
            (
                movement_audit["count"].fillna(0)
                + movement_audit.direction2.fillna(0)
                - movement_audit.count_after.fillna(0)
                - movement_audit.direction2_after.fillna(0)
            ).sum()
        ),
        "identifier_policy": "readable-era-local-date-clock-taxon-v1",
        "count_text_policy": "timed-age-groups-explicit-clock-survey-mismatches-v3",
        "entry_time_policy": "reviewed-point-interval-or-survey-fallback-v1",
        "reviewed_entry_times": len(timing_audit),
        "taxonomy_text_policy": "owner-reviewed-historical-identifications-v1",
        "years": f"{ds.surveys['date'].dt.year.min()}-{ds.surveys['date'].dt.year.max()}",
        "checks": {c.name: c.status for c in checks},
        "table_sha256": {name: _sha256(os.path.join(stage, name)) for name in table_files},
        "interim_sha256": {
            name: _sha256(os.path.join(stage, "interim", name)) for name in interim_files
        },
        "inputs": {
            f: _sha256(os.path.join(ROOT, f))
            for f in raw_files
            + [
                SOURCE_TAXA_FILE,
                AVILIST_FILE,
                EBIRD_FILE,
                "taxonomy/report_taxa.csv",
                "config/attributes/historical_attributes.csv",
                "config/taxonomy/historical_text_mappings.csv",
                "config/schema/datapackage.json",
                "config/survey-status/trektellen-survey-status.csv",
                "config/timing/reviewed-entry-times.csv",
                "config/audit-settings/report-season-windows.csv",
                "config/audit-settings/coverage-season.csv",
                "config/audit-settings/interruption-review-notes.csv",
                "config/audit-settings/historical-gap-breaks.csv",
                "raw/reports/report_text.csv",
                "raw/reports/paper_text.csv",
                "raw/reports/annual-totals.csv",
                "raw/reports/annual-total-pages.csv",
                "raw/reports/observation-interruptions.csv",
                "raw/reports/sources.csv",
            ]
        },
    }
    with open(os.path.join(audit_dir, "report.html"), "w") as f:
        f.write(
            render(
                checks,
                metadata,
                comparison,
                taxonomy_order,
                coverage=coverage,
                coverage_season=coverage_season,
                taxonomy_tree=tree_section(taxon_table, count_table),
            )
        )
    metadata["table_sha256"]["audit/report.html"] = _sha256(os.path.join(audit_dir, "report.html"))
    with open(os.path.join(stage, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    # Compatibility for the forecast's existing two-table reader.
    shutil.copyfile(
        os.path.join(stage, "metadata.json"), os.path.join(processed_dir, "metadata.json")
    )
    if audit["build_status"] == "blocked":
        print(f"Blocking checks failed; previous products retained. Inspect {stage}/audit/.")
        return 1

    # Publish the validated build and refresh generated documentation -------------
    generate_docs(dataset_dir)
    os.makedirs(args.out, exist_ok=True)
    for name in ("dataset", "audit", "gbif"):
        destination = os.path.join(args.out, name)
        if os.path.isdir(destination):
            shutil.rmtree(destination)
        shutil.move(os.path.join(stage, name), destination)
    os.replace(os.path.join(stage, "metadata.json"), os.path.join(args.out, "metadata.json"))
    for name in interim_files + ["processed/metadata.json"]:
        destination = os.path.join(args.interim, name)
        os.makedirs(os.path.dirname(destination), exist_ok=True)
        os.replace(os.path.join(stage, "interim", name), destination)
    shutil.rmtree(stage)
    print(
        f"Wrote {args.out}/ (dataset, audit, GBIF status) and {args.interim}/ (processed, derived, diagnostics)."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
