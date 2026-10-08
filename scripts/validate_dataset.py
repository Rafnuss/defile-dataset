#!/usr/bin/env python3
"""Validate the released CSVs using their adjacent Data Package descriptor."""
import argparse
import json
from pathlib import Path

from defile_dataset.package import validate_package

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--dataset', type=Path, default=Path('output/dataset'))
parser.add_argument('--report', type=Path, help='Optional JSON report path; default is read-only validation.')
args = parser.parse_args()
report = validate_package(args.dataset / 'datapackage.json')
if args.report:
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(f"{'PASS' if report['valid'] else 'FAIL'}: CSV types, constraints, primary/foreign keys and project rules.")
if not report['valid']:
    for task in report.get('tasks', []):
        for error in task.get('errors', [])[:10]:
            print(f"{task['name']}: {error['message']}")
    for error in report.get('x-projectErrors', []):
        print(error)
raise SystemExit(0 if report['valid'] else 1)
