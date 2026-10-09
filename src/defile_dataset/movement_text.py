"""Project explicit non-passage markers onto local counts, retaining native quantities."""

import pandas as pd

NON_PASSAGE = r"(?i)(?:n\s*\.?\s*[np]\s*\.?\s*p\.?|ne passe pas)[.!\s]*"
LOCAL_OVERRIDE = r"(?i)(?:loc|local(?:e|es|s)?|h|(?:en\s+)?halte)[.!\s]*"


def project_non_passage(source):
    """Only standalone markers describe the whole count; uncertain or narrative text stays."""
    result = source.copy()
    fields = [field for field in ("remark", "comment") if field in result]
    override = pd.Series(False, index=result.index)
    matched_fields = {}
    for field in fields:
        matched_fields[field] = (
            result[field].astype("string").str.strip().str.fullmatch(LOCAL_OVERRIDE, na=False)
        )
        override |= matched_fields[field]
    marked = result.remark.astype("string").str.strip().str.fullmatch(NON_PASSAGE, na=False)
    reverse_zero = result.direction2.eq(0) | result.direction2.isna()
    moved = (
        marked & result["count"].gt(0) & (result.local.eq(0) | result.local.isna()) & reverse_zero
    )
    confirmed = marked & result["count"].eq(0) & result.local.gt(0) & reverse_zero
    applied = moved | confirmed
    result.loc[moved, "local"] = result.loc[moved, "count"]
    result.loc[moved, "count"] = 0
    total = source[["count", "direction2", "local"]].sum(axis=1, min_count=1)
    result.loc[override, "local"] = total.loc[override]
    result.loc[override, ["count", "direction2"]] = 0
    for field, matching in matched_fields.items():
        result.loc[matching, field] = pd.NA
        if field + "_residual" in result:
            result.loc[matching, field + "_residual"] = pd.NA
    result.loc[applied, "remark"] = pd.NA
    if "remark_residual" in result:
        result.loc[applied, "remark_residual"] = pd.NA
    note = "Standalone local/non-passage marker represented by local count category."
    applied |= override
    result.loc[applied, "remark_processing"] = (
        result.reindex(columns=["remark_processing"])["remark_processing"].fillna("") + " " + note
    ).str.strip()
    marked |= override
    audit = source.loc[marked, [*fields, "count", "direction2", "local"]].copy()
    audit.insert(
        0,
        "observation_id",
        source.loc[marked, "observation_id"]
        if "observation_id" in source
        else source.index[marked],
    )
    audit["count_after"] = result.loc[marked, "count"]
    audit["local_after"] = result.loc[marked, "local"]
    audit["direction2_after"] = result.loc[marked, "direction2"]
    audit["status"] = "conflicting_or_unquantified"
    audit.loc[confirmed.loc[marked], "status"] = "already_local"
    audit.loc[moved.loc[marked], "status"] = "moved_to_local"
    audit.loc[override.loc[marked], "status"] = "local_override"
    return result, audit
