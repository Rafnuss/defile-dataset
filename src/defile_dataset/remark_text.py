"""Convert explicit residual attributes and event timing without discarding conflicts."""

import re

import pandas as pd

from defile_dataset.attributes import split_daily_context
from defile_dataset.source_text import clock_timestamp, point_from_text

# Hour-only notation is accepted only in a scoped event phrase or a complete range.
EVENT_CLOCK = r"(?:[01]?\d|2[0-3])\s*(?:[:hH]\s*[0-5]\d(?:\s*:\s*[0-5]\d)?|[hH])"
RANGE_CLOCK = rf"(?:{EVENT_CLOCK}|(?:[01]?\d|2[0-3]))"
AGE_PHRASE = r"(?P<label>immatures?|im[m]?[.]?|>\s*1\s*an[s]?)(?!\w)"


def clean_text(values):
    """Trim Unicode whitespace, normalise line endings and represent empty text as missing."""
    return (
        values.astype("string")
        .str.replace(r"\r\n?", "\n", regex=True)
        .str.strip()
        .replace("", pd.NA)
    )


def timing_phrase(text, count):
    """Return clock bounds and residual prose for an explicit whole-record point or range."""
    match = re.fullmatch(
        rf"(?:de\s+)?({RANGE_CLOCK})\s*(?:à|[-–—])\s*({EVENT_CLOCK})[.]?", text, re.I
    )
    if match:
        clocks = [clock if re.search(r"[:hH]", clock) else clock + "h" for clock in match.groups()]
        return clocks, ""
    match = re.fullmatch(r"([01]\d|2[0-3])([0-5]\d)", text)
    if match:
        return [f"{match[1]}:{match[2]}"], ""
    match = re.fullmatch(rf"(?:à\s*)?({EVENT_CLOCK})[.]?", text)
    if match:
        return [match[1]], ""
    parsed = point_from_text(text, count)
    return ([parsed[0]], parsed[1]) if parsed else None


def convert_remark_text(count, survey):
    """Enrich released rows; leave native fields and the source ledger unchanged."""
    count = count.copy()
    count["remark"] = clean_text(count.remark)
    bounds = survey.set_index("survey_id").datetime
    totals = count.groupby(["source_count_id", "count_category"])["count"].sum(min_count=1)
    changes = []
    for i in count.index[count.remark.notna()]:
        row = count.loc[i]
        original = row.remark
        parts = original.split(" | ")
        notes, converted = [], []
        for n, part in enumerate(parts):
            head, context = split_daily_context(part)
            head = head.strip()
            if not head:
                continue
            # Prefixes with their own quantity, uncertainty or prose subject are not whole-row ages.
            age = re.match(rf"^{AGE_PHRASE}(?=$|[\s.,;])", head, re.I)
            uncertain = age and re.match(
                r"\s*(?:(?:probable|possible|peut-être)\b|\?)", head[age.end() :], re.I
            )
            if age and not uncertain and (row.count_category == "normal" or pd.notna(row.age)):
                code = ">1y" if age["label"].startswith(">") else "I"
                existing = count.at[i, "age"]
                if pd.isna(existing) or existing == code:
                    count.at[i, "age"] = code
                    head = head[age.end() :].lstrip(" .;,\n")
                    converted.append("age")
                    if code == "I" and pd.isna(existing):
                        notes.append(
                            "Assumed local convention: immature means >1cy non-adult; inferred from explicit remark."
                        )
                else:
                    notes.append(
                        f'Age text conflict: remark {age["label"]!r} suggests {code}; existing age {existing} retained; wording preserved.'
                    )
            # Raw comments repeat across attribute subgroups: their quantities qualify the source total.
            parsed = (
                timing_phrase(head, totals.loc[(row.source_count_id, row.count_category)])
                if head and "Reviewed timing:" not in str(row.remark_processing)
                else None
            )
            if parsed:
                clocks, remaining = parsed
                native = bounds.get(row.survey_id)
                current = count.at[i, "datetime"]
                support = current if pd.notna(current) else native
                day = pd.Timestamp(str(support).split("/")[0])
                if day.tzinfo:
                    day = day.tz_convert("Europe/Paris").tz_localize(None).normalize()
                timestamps = [clock_timestamp(day, clock) for clock in clocks]
                problem = None
                if any(pd.isna(t) for t in timestamps):
                    problem = "ambiguous local clock"
                elif len(timestamps) == 2 and timestamps[1] <= timestamps[0]:
                    problem = "range has no increasing same-day bounds"
                elif pd.notna(native):
                    start, end = map(pd.Timestamp, native.split("/"))
                    if timestamps[0] < start or timestamps[-1] > end:
                        notes.append(
                            "Recorded count clock outside linked survey; explicit event time retained; survey bounds unchanged."
                        )
                # A timestamp supplies stronger precision than a containing interval or minute clock.
                existing = str(current) if pd.notna(current) else ""
                existing_point = "T" in existing and "/" not in existing
                existing_range = "/" in existing
                if not problem and existing_point:
                    t = pd.Timestamp(existing)
                    agrees = (
                        t.floor("min") == timestamps[0].floor("min")
                        if len(timestamps) == 1
                        else timestamps[0] <= t <= timestamps[1]
                    )
                    if not agrees:
                        problem = "conflicts with existing datetime"
                if not problem and existing_range:
                    start, end = map(pd.Timestamp, existing.split("/"))
                    if timestamps[0] < start or timestamps[-1] > end:
                        problem = "conflicts with existing datetime interval"
                if problem:
                    notes.append(f"Timing text unresolved: {problem}; wording preserved.")
                else:
                    if not existing_point:
                        count.at[i, "datetime"] = "/".join(
                            t.isoformat().replace("+00:00", "Z") for t in timestamps
                        )
                    head = remaining
                    converted.append("datetime")
            parts[n] = "\n\n".join(text for text in (head, context) if text)
        count.at[i, "remark"] = " | ".join(part.strip() for part in parts if part.strip()) or pd.NA
        if notes or "datetime" in converted:
            old = row.remark_processing if pd.notna(row.remark_processing) else ""
            if "datetime" in converted:
                old = old.replace(
                    "Entry time outside the native survey; retained at day level pending correction.",
                    "Entry time outside the native survey; explicit recorded event time retained.",
                )
            count.at[i, "remark_processing"] = (
                " ".join([old, *dict.fromkeys(notes)]).strip() or pd.NA
            )
        if converted or notes:
            changes.append(
                dict(
                    count_id=row.count_id,
                    source_count_id=row.source_count_id,
                    count_category=row.count_category,
                    original_remark=original,
                    remaining_remark=count.at[i, "remark"],
                    converted=", ".join(dict.fromkeys(converted)),
                    age_before=row.age,
                    age_after=count.at[i, "age"],
                    datetime_before=row.datetime,
                    datetime_after=count.at[i, "datetime"],
                    review_note=" ".join(dict.fromkeys(notes)),
                )
            )
    return count, pd.DataFrame(
        changes,
        columns=[
            "count_id",
            "source_count_id",
            "count_category",
            "original_remark",
            "remaining_remark",
            "converted",
            "age_before",
            "age_after",
            "datetime_before",
            "datetime_after",
            "review_note",
        ],
    )
