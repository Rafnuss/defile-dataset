"""The released form of the count and survey tables.

The build works on source codes (Trektellen `~`, `A`, `FC`, Dutch `nno`, `count_category=normal`);
the released CSVs use the words declared in the schema (`x-sourceCodes`: released word -> source
code). This module is the one place where one becomes the other. It also writes every text cell
on one line (`one_line`), so each record is one line of the file.
"""

import re
import unicodedata

import pandas as pd

from defile_dataset.package import columns, descriptor

# Internal column -> released column.
COUNT_RENAMES = {"count_category": "direction"}
# Internal direction -> released word; also the suffix of every released `count_id`.
DIRECTION = {"normal": "main", "reverse": "reverse", "local": "local"}
# Trektellen fills the reverse and local fields with 0 by default: a zero there records nothing.
DEFAULT_ZERO_DIRECTIONS = ("reverse", "local")
# Written where a text cell had a line or paragraph break.
LINE_BREAK = " | "
_BREAKS = re.compile(r"\s*[\n\r\v\f\x85\u2028\u2029]+\s*")
_CONTROL = re.compile(r"[\x00-\x08\x0e-\x1f\x7f\u200b-\u200d\ufeff]")
_SPACES = re.compile(r"\s+")


def one_line(value):
    """A text cell as released: Unicode NFC, line breaks as `LINE_BREAK`, tabs and other spaces
    as one plain space, invisible control characters dropped, no surrounding space. Empty -> NA;
    anything but a string is returned unchanged."""
    if not isinstance(value, str):
        return value
    text = _CONTROL.sub("", unicodedata.normalize("NFC", value)).strip()
    text = _SPACES.sub(" ", _BREAKS.sub(LINE_BREAK, text)).strip()
    return text or pd.NA


def one_line_table(table):
    """`table` with `one_line` applied to every text column."""
    out = table.copy()
    for column in out.columns:
        if out[column].dtype == object or pd.api.types.is_string_dtype(out[column]):
            out[column] = out[column].map(one_line).astype(out[column].dtype)
    return out


def source_codes(resource):
    """{released column: {source code: released word}} for every recoded field of a resource."""
    fields = next(r for r in descriptor()["resources"] if r["name"] == resource)["schema"][
        "fields"
    ]
    return {
        f["name"]: {code: word for word, code in f["x-sourceCodes"].items()}
        for f in fields
        if "x-sourceCodes" in f
    }


def internal_columns(resource):
    """The schema's released columns under their internal names."""
    fields = next(r for r in descriptor()["resources"] if r["name"] == resource)["schema"][
        "fields"
    ]
    internal = {v: k for k, v in COUNT_RENAMES.items()} if resource == "count" else {}
    return [internal.get(f["name"], f["name"]) for f in fields]


def _recode(table, resource):
    out = table.copy()
    for column, mapping in source_codes(resource).items():
        unknown = set(out[column].dropna()) - set(mapping)
        if unknown:
            raise ValueError(f"{resource}.{column}: no released word for {sorted(unknown)}")
        out[column] = out[column].map(mapping, na_action="ignore")
    return out


def release_count(count, survey):
    """`count.csv` as published: default zeros dropped, own time or the survey's, words."""
    out = count.loc[
        ~(count.count_category.isin(DEFAULT_ZERO_DIRECTIONS) & count["count"].eq(0))
    ].rename(columns=COUNT_RENAMES)
    # An entry without a time of its own was counted during its survey: carry that interval.
    interval = out.survey_id.map(survey.set_index("survey_id").datetime)
    out["datetime"] = out.datetime.fillna(interval)
    out = one_line_table(_recode(out, "count"))
    return out.reset_index(drop=True)


def release_survey(survey):
    """`survey.csv` as published: words instead of Dutch weather codes."""
    return one_line_table(_recode(survey, "survey"))


def release_taxonomy(taxonomy):
    """`taxonomy.csv` as published: the schema's columns. The source-name crosswalk
    (`source_taxa`) stays in the build and the repository, not in the release."""
    return one_line_table(taxonomy.reindex(columns=columns("taxonomy")))
