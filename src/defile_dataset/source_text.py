"""Recover explicitly recorded clocks; keep narrative and unresolved timing as text."""

import re

import pandas as pd

from defile_dataset.attributes import split_daily_context
from defile_dataset.read import local_to_utc

CLOCK = r"(?:[01]?\d|2[0-3])\s*[:hH]\s*[0-5]\d(?:\s*:\s*[0-5]\d)?"
CLOCK_TEXT = rf"(?<!\w){CLOCK}(?!\w)"
HISTORICAL_TEXT_COLUMNS = [
    "comment_residual",
    "remark_residual",
    "timing_source",
    "time_text_status",
]


def clock_timestamp(date, clock):
    """Convert a recorded French/local clock to UTC, without inventing a date."""
    clock = re.sub(r"\s+", "", clock).lower().replace("h", ":")
    if clock.endswith(":"):
        clock += "00"
    if clock.count(":") == 1:
        clock += ":00"
    return local_to_utc(pd.Series([pd.Timestamp(date) + pd.Timedelta(clock)])).iloc[0]


def point_from_text(text, count):
    """Recognise a leading event clock or one clock attached to the whole count."""
    if pd.isna(text):
        return None
    text = str(text).strip()
    # 'vers', durations, survey narratives and reported movements of other birds are not points.
    match = re.match(rf"^(?:(?P<count>\d+)\s+)?(?:à\s*)?(?P<clock>{CLOCK})(?!\w)", text)
    if match:
        if match["count"] and int(match["count"]) != count:
            return None
        remaining = text[match.end() :].strip(" .;,–-\n")
        if re.match(
            rf"^(?:{CLOCK}|(?:à\s*){CLOCK}|\d+\s*(?:à|:)\s*{CLOCK}|de\s|d[’']|pour\s|environ\b|\?)",
            remaining,
        ):
            return None
        return match["clock"], remaining
    match = re.fullmatch(
        rf"(?P<description>(?:\d+\s+(?:adultes?|jeunes?)\s*,?\s*)+)à\s*(?P<clock>{CLOCK})[.!]?",
        text,
    )
    if match and sum(map(int, re.findall(r"\d+", match["description"]))) == count:
        return match["clock"], match["description"].strip(" ,")
    return None


def recover_historical_times(rows):
    """Use Naturalist entry clocks, then unambiguous count comments; preserve source fields."""
    rows = rows.copy()
    local = rows.date + pd.to_timedelta(rows.time_local.astype("string"))
    rows["datetime_original"] = local_to_utc(local)
    rows["datetime"] = rows.datetime_original
    rows["timing_source"] = pd.Series(pd.NA, index=rows.index, dtype="string")
    rows.loc[rows.time_local.notna(), "timing_source"] = "time_local"
    rows["time_text_status"] = pd.Series(pd.NA, index=rows.index, dtype="string")
    for field in ("comment", "remark"):
        rows[field + "_residual"] = rows[field].astype("string")
        candidates = rows[field].fillna("").str.contains(CLOCK_TEXT, regex=True)
        for i in rows.index[candidates]:
            parsed = point_from_text(rows.at[i, field], rows.at[i, "count"])
            if parsed is None:
                rows.at[i, "time_text_status"] = "not_a_single_count_time"
                continue
            clock, remaining = parsed
            timestamp = clock_timestamp(rows.at[i, "date"], clock)
            if pd.isna(timestamp):
                rows.at[i, "time_text_status"] = "ambiguous_local_clock"
            elif pd.notna(rows.at[i, "datetime"]) and rows.at[i, "datetime"] != timestamp:
                rows.at[i, "time_text_status"] = "conflicting_recorded_clocks"
            else:
                rows.at[i, "datetime"] = timestamp
                rows.at[i, "datetime_original"] = timestamp
                if pd.isna(rows.at[i, "timing_source"]):
                    rows.at[i, "timing_source"] = field
                rows.at[i, field + "_residual"] = remaining or pd.NA
                rows.at[i, "time_text_status"] = "clock_converted"
    return rows


def timed_groups(text, count):
    """Parse a complete list of explicit quantity/clock pairs, never a range or duration."""
    events = timed_events(text, count)
    return [(event["count"], event["clock"]) for event in events] if events else None


def timed_events(text, count):
    """Keep age descriptions attached to their explicitly timed flock."""
    if pd.isna(text):
        return None
    head, _ = split_daily_context(text)
    parts = re.split(
        r"\s*(?:;|[-–—]|\bet\b|,)\s*(?=\d)(?![^()]*\))",
        " ".join(head.split()).rstrip("."),
        flags=re.I,
    )
    if len(parts) < 2:
        return None
    groups = []
    for part in parts:
        match = re.fullmatch(
            rf"(?P<count>\d+)\s*(?P<description>.*?)\s*(?:à|:)\s*(?P<clock>{CLOCK})", part, re.I
        )
        if match is None:
            return None
        groups.append(
            dict(
                count=int(match["count"]),
                clock=match["clock"],
                description=match["description"].strip(" ()"),
            )
        )
    return groups if sum(group["count"] for group in groups) == count else None


def timed_age_components(quantity, description):
    """Convert explicit ages; retain unexplained flock descriptors and unaged remainders."""
    age_label = r"(?:adultes?|ad\.?|jeunes?|juv\.?|1\s*ac)"
    if re.fullmatch(age_label, description, re.I):
        return [(quantity, "A" if description.lower().startswith(("ad", "adult")) else "1", "")]
    matches = list(re.finditer(rf"(?P<count>\d+)\s*(?P<age>{age_label})(?!\w)", description, re.I))
    if not matches:
        return [(quantity, None, description)]
    parts = [
        (int(match["count"]), "A" if match["age"].lower().startswith("ad") else "1", "")
        for match in matches
    ]
    if sum(part[0] for part in parts) > quantity:
        return None
    residual = re.sub(rf"\d+\s*{age_label}(?!\w)", "", description, flags=re.I)
    residual = re.sub(r"\b(?:et|avec)\b|[,;]", " ", residual, flags=re.I).strip()
    if sum(part[0] for part in parts) < quantity:
        parts.append((quantity - sum(part[0] for part in parts), None, residual))
    elif residual:
        parts = [(n, age, residual) for n, age, _ in parts]
    return parts


def split_timed_counts(normal):
    """Split fully accounted timed groups only when their attributes are interchangeable."""
    has_clock = (
        normal.reindex(columns=["comment", "remark"])
        .fillna("")
        .apply(lambda values: values.str.contains(CLOCK_TEXT, regex=True))
        .any(axis=1)
    )
    reviewed = (
        normal.reindex(columns=["flags"])["flags"]
        .astype("string")
        .str.contains("reviewed_time_", na=False)
    )
    candidates = normal.source.eq("historical") & normal.datetime.isna() & has_clock & ~reviewed
    timed, intervals = {}, {}
    for source_id, rows in normal.loc[candidates].groupby("source_count_id", sort=False):
        row = rows.iloc[0]
        for field in ("comment", "remark"):
            groups = timed_events(row.get(field), rows["count"].sum())
            if groups is None:
                continue
            clocks = [clock_timestamp(row.date, group["clock"]) for group in groups]
            if any(pd.isna(clock) for clock in clocks):
                continue
            # A whole-row age total does not say which timed flock contains those birds.
            fields = ["sex", "plumage", "detail", "details"]
            if len(rows.reindex(columns=fields).fillna("").drop_duplicates()) != 1:
                intervals[source_id] = clocks
                continue
            parts = [
                timed_age_components(group["count"], group["description"]) for group in groups
            ]
            if any(part is None for part in parts):
                intervals[source_id] = clocks
                continue
            explicit_ages = any(age for group in parts for _, age, _ in group)
            if not explicit_ages and rows.age.nunique(dropna=False) > 1:
                intervals[source_id] = clocks
                continue
            if explicit_ages and rows.age.notna().any():
                original = (
                    rows.assign(age=rows.age.fillna("")).groupby("age")["count"].sum().to_dict()
                )
                described = {}
                for group in parts:
                    for quantity, age, _ in group:
                        described[age or ""] = described.get(age or "", 0) + quantity
                if original != described:
                    # Subtract explicit timed ages from recorded totals. Only a unique remainder is assignable.
                    deficits = {
                        age: original.get(age, 0) - described.get(age, 0)
                        for age in sorted(set(original) | (set(described) - {""}))
                        if age
                    }
                    deficits[""] = original.get("", 0)
                    unknown = [
                        (g, p)
                        for g, group in enumerate(parts)
                        for p, (_, age, _) in enumerate(group)
                        if age is None
                    ]
                    remaining = sum(parts[g][p][0] for g, p in unknown)
                    positive = {age: n for age, n in deficits.items() if n > 0}
                    if (
                        min(deficits.values()) < 0
                        or sum(deficits.values()) != remaining
                        or not unknown
                        or (len(positive) > 1 and len(unknown) > 1)
                    ):
                        intervals[source_id] = clocks
                        continue
                    if len(positive) == 1:
                        age = next(iter(positive))
                        for g, p in unknown:
                            quantity, _, residual = parts[g][p]
                            parts[g][p] = (quantity, age or None, residual)
                    else:
                        g, p = unknown[0]
                        residual = parts[g][p][2]
                        parts[g][p : p + 1] = [
                            (quantity, age or None, residual) for age, quantity in positive.items()
                        ]
            timed[source_id] = (field, parts, clocks, explicit_ages)
            intervals.pop(source_id, None)
            break
    if intervals:
        normal = normal.copy()
        for source_id, clocks in intervals.items():
            mask = normal.source_count_id.eq(source_id)
            normal.loc[mask, "datetime_interval"] = "/".join(
                clock.isoformat().replace("+00:00", "Z")
                for clock in sorted(set([min(clocks), max(clocks)]))
            )
            note = "Timed flocks retained as an observation interval; recorded ages/sex/plumage cannot be uniquely assigned to individual clock groups; flock details remain in remarks."
            normal.loc[mask, "remark_processing"] = (
                normal.reindex(columns=["remark_processing"])
                .loc[mask, "remark_processing"]
                .fillna("")
                + " "
                + note
            ).str.strip()
    if not timed:
        return normal
    result, indexes = [], []
    for source_id, (field, groups, clocks, explicit_ages) in timed.items():
        template = normal.loc[normal.source_count_id.eq(source_id)].iloc[0]
        row = template.to_dict()
        _, context = split_daily_context(template.get(field))
        for number, (parts, timestamp) in enumerate(zip(groups, clocks), 1):
            for component, (quantity, age, residual) in enumerate(parts, 1):
                result.append(
                    dict(
                        row,
                        observation_id=f"{source_id}-time{number}"
                        + (f"-age{component}" if len(parts) > 1 else ""),
                        count=quantity,
                        datetime=timestamp,
                        time_resolution="point",
                        age=(age or pd.NA) if explicit_ages else row.get("age"),
                        **{
                            field
                            + "_residual": "\n\n".join(
                                text for text in (residual, context) if text
                            )
                            or pd.NA
                        },
                    )
                )
                indexes.append(template.name)
    retained = normal.loc[~normal.source_count_id.isin(timed)]
    return (
        pd.concat([retained, pd.DataFrame(result, index=indexes)])
        .sort_index(kind="stable")
        .reset_index(drop=True)
    )
