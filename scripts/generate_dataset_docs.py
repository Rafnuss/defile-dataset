#!/usr/bin/env python3
"""Copy the authoritative descriptor and generate column documentation from it."""
import argparse
from pathlib import Path

from defile_dataset.package import generate_docs

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--out", type=Path, default=Path("output/dataset"))
args = parser.parse_args()
generate_docs(args.out)
print(f"Generated {args.out}/README.md, datapackage.json and the repository dictionaries.")
