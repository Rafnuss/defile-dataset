"""A dataset release: the tagged, frozen copy of a build that everything downstream reads.

The release is `dataset.zip` on a GitHub release of this repo, tagged `vYYYY.N`. It holds the
Zenodo upload (`output/zenodo/`) and the build's `metadata.json` (`output/audit/`), which gives
each file's sha256.
defile-passage builds from a tag; the Zenodo record and the GBIF export are made from the same
files. `scripts/release_dataset.py` checks the build and publishes it.
"""

import hashlib
import json
import re
import zipfile
from pathlib import Path

ASSET = "dataset.zip"  # the name defile-passage downloads
TAG = re.compile(r"^v\d{4}\.\d+$")  # vYYYY.N: the year of the last season, then a counter
UPLOAD_DIR = "zenodo"  # under the output folder: the files of the release
METADATA_FILE = "metadata.json"  # at the zip's root
METADATA_PATH = "audit/metadata.json"  # in the output folder
UNCOMMITTED = "(uncommitted changes)"  # as build.py marks a build from uncommitted code
FAILED = "fail"  # a check's status in metadata.json


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def problems(output: Path, head: str, tag: str) -> list[str]:
    """Why the build in `output` cannot be released as `tag` from commit `head` (empty when it
    can)."""
    out = []
    if not TAG.match(tag):
        out.append(f"tag {tag!r} is not vYYYY.N")
    metadata = json.loads((output / METADATA_PATH).read_text(encoding="utf-8"))
    sha = metadata.get("git_sha", "")
    if UNCOMMITTED in sha:
        out.append("built from uncommitted code: commit, then build again")
    elif sha != head:
        out.append(f"built at {sha[:7]}, HEAD is {head[:7]}: build again")
    failed = [name for name, status in metadata.get("checks", {}).items() if status == FAILED]
    if failed:
        out.append(f"failed checks: {', '.join(failed)}")
    hashes = metadata.get("table_sha256", {})
    folder = output / UPLOAD_DIR
    files = sorted(p.name for p in folder.iterdir() if p.is_file())
    expected = sorted(k.split("/", 1)[1] for k in hashes if k.startswith(UPLOAD_DIR + "/"))
    if files != expected:
        out.append(f"{UPLOAD_DIR}/ holds {files}, the build wrote {expected}: build again")
    changed = [
        f for f in files if f in expected and sha256(folder / f) != hashes[f"{UPLOAD_DIR}/{f}"]
    ]
    if changed:
        out.append(f"changed since the build: {', '.join(changed)}: build again")
    return out


def pack(output: Path, path: Path) -> Path:
    """`dataset.zip`: the upload files and `metadata.json`, at the zip's root."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted((output / UPLOAD_DIR).iterdir()):
            z.write(f, f.name)
        z.write(output / METADATA_PATH, METADATA_FILE)
    return path
