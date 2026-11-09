#!/usr/bin/env python3
"""Publish the current build as a dataset release: `dataset.zip` on a GitHub release tagged
`vYYYY.N` (`defile_dataset.release`).

Refused: a build from uncommitted code or from another commit than HEAD, a commit not pushed, a
failed check, a file in `output/zenodo/` changed since the build, a tag that already exists.

Usage:
    uv run python scripts/release_dataset.py v2026.1 --dry-run   # the checks and the zip only
    uv run python scripts/release_dataset.py v2026.1
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

from defile_dataset import release as R

ROOT = Path(__file__).resolve().parents[1]


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True, cwd=ROOT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tag", help="vYYYY.N")
    ap.add_argument("--output", type=Path, default=ROOT / "output")
    ap.add_argument("--dry-run", action="store_true", help="check and zip, publish nothing")
    args = ap.parse_args(argv)

    head = run("git", "rev-parse", "HEAD").stdout.strip()
    problems = R.problems(args.output, head, args.tag)
    if not run("git", "branch", "-r", "--contains", head).stdout.strip():
        problems.append(f"{head[:7]} is not pushed")
    if run("gh", "release", "view", args.tag).returncode == 0:
        problems.append(f"release {args.tag} already exists: a release is never replaced")
    if problems:
        raise SystemExit("Not released:\n  " + "\n  ".join(problems))

    # The zip lives only as long as the upload: the release on GitHub is its copy
    with tempfile.TemporaryDirectory() as tmp:
        path = R.pack(args.output, Path(tmp) / R.ASSET)
        print(f"{R.ASSET}: {path.stat().st_size / 1e6:.1f} MB, from {head[:7]}")
        if args.dry_run:
            print("Dry run: nothing published")
            return 0
        notes = (
            f"Dataset {args.tag}, built from {head[:7]}. `{R.ASSET}` holds the Zenodo upload and"
            " the build's metadata.json (sha256 of each file)."
        )
        made = run(
            "gh", "release", "create", args.tag, str(path),
            "--target", head, "--title", f"Dataset {args.tag}", "--notes", notes,
        )  # fmt: skip
    if made.returncode:
        raise SystemExit(made.stderr)
    print(f"Released {args.tag}: build defile-passage with --dataset {args.tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
