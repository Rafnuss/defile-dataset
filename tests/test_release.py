import json
import zipfile

from defile_dataset import release as R

HEAD = "a" * 40


def _build(tmp_path, git_sha=HEAD, checks=None):
    folder = tmp_path / R.UPLOAD_DIR
    folder.mkdir()
    (folder / "count.csv").write_text("taxon_id,count\nx,1\n")
    hashes = {f"{R.UPLOAD_DIR}/count.csv": R.sha256(folder / "count.csv")}
    metadata = {"git_sha": git_sha, "checks": checks or {"x": "pass"}, "table_sha256": hashes}
    (tmp_path / R.METADATA_PATH).parent.mkdir()
    (tmp_path / R.METADATA_PATH).write_text(json.dumps(metadata))
    return tmp_path


def test_clean_build_can_be_released(tmp_path):
    assert R.problems(_build(tmp_path), HEAD, "v2026.1") == []


def test_refused(tmp_path):
    out = _build(tmp_path, git_sha=HEAD + " " + R.UNCOMMITTED, checks={"x": "fail"})
    (out / R.UPLOAD_DIR / "count.csv").write_text("edited\n")
    (out / R.UPLOAD_DIR / "extra.csv").write_text("\n")
    found = " ".join(R.problems(out, HEAD, "2026"))
    for expected in ("vYYYY.N", "uncommitted", "failed checks", "extra.csv"):
        assert expected in found


def test_changed_file_refused(tmp_path):
    out = _build(tmp_path)
    (out / R.UPLOAD_DIR / "count.csv").write_text("edited\n")
    assert any("changed since the build" in p for p in R.problems(out, HEAD, "v2026.1"))


def test_pack(tmp_path):
    out = _build(tmp_path)
    with zipfile.ZipFile(R.pack(out, tmp_path / R.ASSET)) as z:
        assert sorted(z.namelist()) == ["count.csv", R.METADATA_FILE]
