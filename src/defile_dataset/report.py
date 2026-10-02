"""Self-contained HTML report of a built dataset: checks, entry errors, corrections, coverage.

Rendering only: every number comes from the `Dataset` and the `Check`s. Times in tables are
local (Europe/Paris), as in the raw files, so a row can be looked up there.
"""

import datetime as dt
import html
import re

import pandas as pd

from defile_dataset.build import Dataset
from defile_dataset.checks import Check
from defile_dataset.site import SITE_NAME, TIMEZONE

MAX_TABLE_ROWS = 200
STATUS_COLORS = {"pass": "#1a7f37", "warn": "#9a6700", "fail": "#cf222e"}
ISSUE_ENTRY_COLUMNS = [
    "observation_id",
    "survey_id",
    "datetime_original",
    "taxon_name_original",
    "count",
    "flags",
]

CSS = """
:root { --fg:#1f2328; --muted:#59636e; --bg:#ffffff; --line:#d1d9e0; --soft:#f6f8fa; }
body { font: 14px/1.5 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; color: var(--fg);
       background: var(--bg); max-width: 1180px; margin: 0 auto; padding: 24px 16px 80px; }
h1 { font-size: 24px; margin-bottom: 4px; } h2 { margin-top: 40px; border-bottom: 1px solid
var(--line); padding-bottom: 4px; } h3 { margin-top: 24px; }
.muted { color: var(--muted); }
table { border-collapse: collapse; margin: 8px 0 16px; font-size: 12.5px; }
th, td { border: 1px solid var(--line); padding: 3px 8px; text-align: right; vertical-align: top; }
th { background: var(--soft); } td.l, th.l { text-align: left; }
.table-wrap { overflow-x: auto; max-width: 100%; }
.badge { display: inline-block; min-width: 40px; text-align: center; color: #fff;
         border-radius: 10px; padding: 0 8px; font-size: 12px; font-weight: 600; }
details { margin: 4px 0 12px; } summary { cursor: pointer; color: var(--muted); }
.callout { border-left: 4px solid #cf222e; background: #fff5f5; padding: 8px 12px; }
code { background: var(--soft); padding: 1px 4px; border-radius: 4px; }
"""


def _local(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for c in df.columns:
        if isinstance(df[c].dtype, pd.DatetimeTZDtype):
            df[c] = df[c].dt.tz_convert(TIMEZONE).dt.strftime("%Y-%m-%d %H:%M")
        elif pd.api.types.is_datetime64_any_dtype(df[c]):
            df[c] = df[c].dt.strftime("%Y-%m-%d")
    return df


def _table(df: pd.DataFrame, max_rows=MAX_TABLE_ROWS) -> str:
    if df is None or df.empty:
        return '<p class="muted">No rows.</p>'
    more = len(df) - max_rows
    out = _local(df.head(max_rows)).to_html(index=False, na_rep="", border=0)
    note = f'<p class="muted">… and {more} more rows.</p>' if more > 0 else ""
    return f'<div class="table-wrap">{out}</div>{note}'


def _badge(status: str) -> str:
    return f'<span class="badge" style="background:{STATUS_COLORS[status]}">{status}</span>'


def _section_checks(checks: list[Check]) -> str:
    rows = "".join(
        f'<tr><td class="l">{html.escape(c.name)}</td><td>{_badge(c.status)}</td>'
        f'<td class="l">{html.escape(c.detail)}</td></tr>'
        for c in checks
    )
    details = "".join(
        f"<details><summary>{html.escape(c.name)}: {len(c.rows)} rows</summary>"
        f"{_table(c.rows)}</details>"
        for c in checks
        if not c.rows.empty
    )
    return (
        "<h2>Checks</h2>"
        '<table><tr><th class="l">Check</th><th>Status</th><th class="l">Detail</th></tr>'
        f"{rows}</table>{details}"
    )


def _section_issues(ds: Dataset) -> str:
    issues = ds.issues
    parts = [
        "<h2>Trektellen entries to correct</h2>",
        '<p class="muted">Entry errors found while building, one row per count and issue, '
        "with the species and birds concerned. Each is handled here (see the flag in the "
        "entries below), but correcting it in Trektellen and re-exporting is better: the "
        "automatic handling is a guess.</p>",
    ]
    if issues.empty:
        return "".join(parts) + "<p>None.</p>"
    summary = (
        issues.groupby("issue")
        .agg(counts=("survey_id", "nunique"), entries=("entries", "sum"), birds=("birds", "sum"))
        .reset_index()
    )
    table = issues.assign(
        period=issues["start"].dt.tz_convert(TIMEZONE).dt.strftime("%H:%M")
        + "–"
        + issues["end"].dt.tz_convert(TIMEZONE).dt.strftime("%H:%M"),
        trektellen_count=issues["survey_id"].str.removeprefix("T"),
    )[["date", "trektellen_count", "period", "issue", "detail", "entries", "birds"]]
    parts += [_table(summary), _table(table, max_rows=len(table))]

    o = ds.observations
    entries = o[o["survey_id"].isin(issues["survey_id"]) & (o["flags"] != "")]
    entries = entries[~entries["flags"].str.fullmatch("time_adjusted")]
    parts.append(
        f"<details><summary>The {len(entries)} flagged entries of these counts</summary>"
        f"{_table(entries[ISSUE_ENTRY_COLUMNS], max_rows=len(entries))}</details>"
    )
    return "".join(parts)


def _section_flags(ds: Dataset) -> str:
    def count(df, by_birds):
        f = df.assign(flag=df["flags"].str.split(";")).explode("flag")
        f = f[f["flag"].fillna("") != ""]
        agg = {"rows": ("flag", "size")}
        if by_birds:
            agg["birds"] = ("count", "sum")
        return f.groupby(["source", "flag"]).agg(**agg).reset_index()

    return (
        "<h2>Corrections and flags</h2>"
        '<p class="muted">Rows are never removed: each correction flags its rows (and keeps '
        "the original value in <code>*_original</code>). See README.md for each flag.</p>"
        "<h3>Surveys</h3>"
        + _table(count(ds.surveys, False))
        + "<h3>Observations</h3>"
        + _table(count(ds.observations, True))
    )


def _section_years(ds: Dataset) -> str:
    s = ds.surveys.assign(
        year=ds.surveys["date"].dt.year,
        hours=(ds.surveys["end"] - ds.surveys["start"]).dt.total_seconds() / 3600,
    )
    o = ds.observations.assign(year=ds.observations["date"].dt.year)
    t = (
        s.groupby(["source", "year"])
        .agg(surveys=("survey_id", "size"), survey_hours=("hours", "sum"))
        .join(o.groupby(["source", "year"]).agg(observations=("observation_id", "size")))
        .join(o.groupby(["source", "year"])["count"].sum().rename("birds"))
        .join(
            o[o["flags"] != ""].groupby(["source", "year"]).size().rename("flagged_observations")
        )
        .fillna(0)
        .round(0)
        .astype(int)
        .reset_index()
    )
    tk = o[o["source"] == "trektellen"]
    fields = ["age", "sex", "plumage", "remark", "direction2", "local"]
    comp = (
        tk.groupby("year")[fields].agg(lambda x: int((x.notna() & (x != 0)).sum())).reset_index()
    )
    sv = s[s["source"] == "trektellen"]
    scomp = (
        sv.groupby("year")[["observers", "weather", "observers_active", "temperature"]]
        .agg(lambda x: int((x.notna() & (x != 0)).sum()))
        .join(sv.groupby("year").size().rename("surveys"))
        .reset_index()
    )
    return (
        "<h2>Coverage per year</h2>"
        + _table(t, max_rows=200)
        + "<h3>Trektellen observations with a value (non-empty, non-zero)</h3>"
        + _table(comp)
        + "<h3>Trektellen surveys with a value</h3>"
        + _table(scomp)
    )


def render(ds: Dataset, checks: list[Check], metadata: dict) -> str:
    status = {k: sum(c.status == k for c in checks) for k in STATUS_COLORS}
    n_issues = ds.issues["survey_id"].nunique()
    meta = "".join(
        f'<tr><td class="l">{html.escape(str(k))}</td><td class="l">{html.escape(str(v))}</td></tr>'
        for k, v in metadata.items()
        if not isinstance(v, (dict, list))
    )
    body = (
        f"<h1>{SITE_NAME} count dataset</h1>"
        f'<p class="muted">Built {dt.datetime.now():%Y-%m-%d %H:%M} by '
        "<code>scripts/build_dataset.py</code>.</p>"
        f"<p>{len(ds.surveys):,} surveys, {len(ds.observations):,} observations, "
        f"{ds.observations['count'].sum():,.0f} birds. Checks: "
        f"{_badge('pass')} {status['pass']} {_badge('warn')} {status['warn']} "
        f"{_badge('fail')} {status['fail']}</p>"
        f'<p class="callout"><b>{n_issues} Trektellen counts with entries to correct</b> '
        "(section 2).</p>"
        f"<table>{meta}</table>"
        + _section_checks(checks)
        + _section_issues(ds)
        + _section_flags(ds)
        + _section_years(ds)
    )
    n = iter(range(1, 100))
    body = re.sub("<h2>", lambda m: f"<h2>{next(n)}. ", body)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>Count dataset report</title><style>{CSS}</style></head>"
        f"<body>{body}</body></html>"
    )
