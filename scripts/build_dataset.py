#!/usr/bin/env python3
"""Builds the dataset from `raw/`: `output/surveys.csv`, `output/observations.csv`,
`output/entry_issues.csv`, `output/metadata.json` and `output/report.html`.

Usage:
    uv run python scripts/build_dataset.py
    uv run python scripts/build_dataset.py --out /some/dir
"""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

from defile_dataset import read  # noqa: E402
from defile_dataset.build import build  # noqa: E402
from defile_dataset.checks import run_checks  # noqa: E402
from defile_dataset.report import render  # noqa: E402

RAW_DIR = os.path.join(ROOT, "raw")
TAXONOMY_FILE = os.path.join(ROOT, "taxonomy", "taxonomy.csv")


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
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    args = ap.parse_args(argv)

    years = read.trektellen_years(RAW_DIR)
    print(f"Reading {read.HISTORICAL_FILE} and Trektellen {years} ...")
    hist = read.read_historical(RAW_DIR)
    sightings, counts = read.read_trektellen(RAW_DIR)
    taxonomy = read.read_taxonomy(TAXONOMY_FILE)

    ds = build(hist, sightings, counts, taxonomy)
    checks = run_checks(ds)
    for c in checks:
        print(f"  [{c.status:4s}] {c.name}: {c.detail}")
    print(f"  {ds.issues['survey_id'].nunique()} Trektellen counts with entries to correct.")

    os.makedirs(args.out, exist_ok=True)
    _write_csv(ds.surveys, os.path.join(args.out, "surveys.csv"))
    _write_csv(ds.observations, os.path.join(args.out, "observations.csv"))
    _write_csv(ds.issues, os.path.join(args.out, "entry_issues.csv"))

    raw_files = sorted(
        os.path.relpath(os.path.join(d, f), ROOT)
        for d, _, fs in os.walk(RAW_DIR)
        for f in fs
        if f.endswith(".xlsx")
    )
    dirty = bool(_git("status", "--porcelain", "--", "raw", "taxonomy", "src"))
    metadata = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_sha": _git("rev-parse", "HEAD") + (" (uncommitted changes)" if dirty else ""),
        "surveys": len(ds.surveys),
        "observations": len(ds.observations),
        "birds": int(ds.observations["count"].sum()),
        "years": f"{ds.surveys['date'].dt.year.min()}-{ds.surveys['date'].dt.year.max()}",
        "checks": {c.name: c.status for c in checks},
        "inputs": {
            f: _sha256(os.path.join(ROOT, f)) for f in raw_files + ["taxonomy/taxonomy.csv"]
        },
    }
    with open(os.path.join(args.out, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    with open(os.path.join(args.out, "report.html"), "w") as f:
        f.write(render(ds, checks, metadata))
    print(
        f"Wrote {args.out}/: surveys.csv, observations.csv, entry_issues.csv, metadata.json, report.html"
    )
    return 1 if any(c.status == "fail" for c in checks) else 0


if __name__ == "__main__":
    sys.exit(main())
