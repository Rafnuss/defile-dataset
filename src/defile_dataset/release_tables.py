"""The released form of the count and survey tables.

The build works on source codes (Trektellen `~`, `A`, `FC`, Dutch `nno`, `count_category=normal`);
the released CSVs use the words declared in the schema (`x-sourceCodes`: released word -> source
code). This module is the one place where one becomes the other.
"""

import pandas as pd

from defile_dataset.package import descriptor

# Internal column -> released column.
COUNT_RENAMES = {"count_category": "direction"}
# Internal direction -> released word; also the suffix of every released `count_id`.
DIRECTION = {"normal": "main", "reverse": "reverse", "local": "local"}
# Trektellen fills the reverse and local fields with 0 by default: a zero there records nothing.
DEFAULT_ZERO_DIRECTIONS = ("reverse", "local")


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
    out = _recode(out, "count")
    return out.reset_index(drop=True)


def release_survey(survey):
    """`survey.csv` as published: words instead of Dutch weather codes."""
    return _recode(survey, "survey")
