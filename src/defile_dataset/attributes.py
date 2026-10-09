"""Parse historical subgroups once for attribute mapping, released rows and audit."""

import re
import unicodedata

import pandas as pd

ATTRIBUTE_COLUMNS = ["age", "sex", "plumage", "remark_processing"]
DAILY_CONTEXT = r"(?:^|\n\n)\[(?:Rapport annuel|Nos Oiseaux) [^;\n]+; Contexte journalier "


def split_daily_context(text):
    """Separate recorded attributes from explicitly attributed published day-level prose."""
    if pd.isna(text):
        return "", ""
    match = re.search(DAILY_CONTEXT, str(text))
    return (
        (str(text)[: match.start()], str(text)[match.start() :].strip())
        if match
        else (str(text), "")
    )


def normalize_label(text):
    """Ignore casing/spacing and the separate flight annotation, retaining French accents."""
    text = unicodedata.normalize("NFC", text).lower()
    return re.sub(r"\s*\(en vol\)$", "", " ".join(text.split())).strip()


def historical_attributes(hist, crosswalk):
    """Return source-row attributes and parsed subgroups, preserving the source total."""
    lookup = crosswalk.fillna("").set_index(["source_sheet", "label"])
    values = pd.DataFrame(pd.NA, index=hist.index, columns=ATTRIBUTE_COLUMNS, dtype="string")
    audit = []
    for i, row in hist.iterrows():
        field = "details" if row["sheet"] == "2017-2021" else "detail"
        detail = row.get(field)
        if pd.isna(detail):
            continue
        # Published day-level context is prose, not recorded age/sex subgroups.
        detail, _ = split_daily_context(detail)
        if not detail.strip():
            continue
        parts, notes, quantities, components = [], [], [], []
        status = "mapped"
        review_needed = False
        for component in str(detail).split("/"):
            match = re.fullmatch(r"\s*(\d+)\s*x(?:\s+(.*?))?\s*", component)
            if match is None:
                status = "unparsed"
                notes.append("Unrecognised detail format; attributes left unassigned.")
                break
            quantities.append(int(match[1]))
            label = normalize_label(match[2] or "")
            residual = match[2] or ""
            if (row["sheet"], label) in lookup.index:
                mapped = lookup.loc[(row["sheet"], label)]
                parts.append([mapped[a] for a in ("age", "sex", "plumage")])
                converted = not label or (
                    any(parts[-1])
                    and (
                        not mapped["note"]
                        or mapped["note"].startswith("Assumed local convention:")
                    )
                )
                if mapped["sex"] and mapped["note"].startswith("Age unresolved:"):
                    residual = re.sub(r"^(?:mâles?|femelles?)\s+", "", label)
                if mapped["note"]:
                    notes.append(mapped["note"])
                    review_needed |= label != "(entendu)"
            else:
                converted = not label
                parts.append(["", "", ""])
                if label:
                    notes.append(f"Unmapped detail phrase: {label}.")
                    review_needed = True
            components.append(
                dict(
                    component_count=quantities[-1],
                    description=match[2] or "",
                    residual="" if converted else residual,
                    **dict(zip(("age", "sex", "plumage"), parts[-1])),
                )
            )
        if status != "unparsed":
            if sum(quantities) > row["count"]:
                status = "quantity_mismatch"
                notes.append(
                    "Detail quantities exceed the source count; source total retained without splitting."
                )
            else:
                if sum(quantities) == row["count"]:
                    for j, attribute in enumerate(("age", "sex", "plumage")):
                        codes = [
                            part[j] for part, quantity in zip(parts, quantities) if quantity > 0
                        ]
                        if codes and codes[0] and len(set(codes)) == 1:
                            values.at[i, attribute] = codes[0]
                if sum(quantities) < row["count"]:
                    components.append(
                        dict(
                            component_count=row["count"] - sum(quantities),
                            description="Undescribed remainder",
                            residual="",
                            age="",
                            sex="",
                            plumage="",
                        )
                    )
                if review_needed:
                    status = "partial" if any(any(part) for part in parts) else "unassigned"
        note = " ".join(dict.fromkeys(notes))
        if note:
            values.at[i, "remark_processing"] = note
        audit.append(
            {
                "observation_id": f"H-{row['sheet']}-r{row['row']}",
                "date": row["date"],
                "sheet": row["sheet"],
                "row": row["row"],
                "count": row["count"],
                "detail": detail,
                "status": status,
                "components": components if status != "unparsed" else [],
                "detail_total": sum(quantities) if status != "unparsed" else pd.NA,
                **values.loc[i].to_dict(),
            }
        )
    return values, pd.DataFrame(audit)


def quantity_components(attributes):
    """Flatten the parsed components, including normal undescribed remainders."""
    rows = []
    for record in attributes.to_dict("records"):
        if record["status"] == "unparsed":
            continue
        base = {
            key: record[key]
            for key in ("observation_id", "date", "sheet", "row", "detail", "status")
        }
        base.update(
            source_count=record["count"],
            detail_total=record["detail_total"],
            source_minus_detail=record["count"] - record["detail_total"],
        )
        positive = sum(p["component_count"] > 0 for p in record["components"])
        for number, part in enumerate(record["components"], 1):
            released_id = record["observation_id"] + (
                "-part" + str(number) if positive > 1 else ""
            )
            rows.append(
                dict(
                    base,
                    component=number,
                    released_count_id=released_id
                    if record["status"] != "quantity_mismatch" and part["component_count"] > 0
                    else pd.NA,
                    **part,
                )
            )
    return pd.DataFrame(
        rows,
        columns=[
            "observation_id",
            "date",
            "sheet",
            "row",
            "status",
            "source_count",
            "detail_total",
            "source_minus_detail",
            "component",
            "released_count_id",
            "component_count",
            "description",
            "residual",
            "age",
            "sex",
            "plumage",
            "detail",
        ],
    )


def split_historical_counts(observations, components):
    """Split valid subgroups; keep source records unchanged for conservation checks."""
    rows = []
    groups = dict(
        tuple(
            components.loc[
                components.source_minus_detail.ge(0) & components.component_count.gt(0)
            ].groupby("observation_id", sort=False)
        )
    )
    observations = observations.reset_index(drop=True)
    split = observations.observation_id.isin(groups.keys())
    # Only split records are expanded row by row; the rest keep their order.
    for position, row in zip(
        observations.index[split], observations.loc[split].to_dict("records")
    ):
        for part in groups[row["observation_id"]].to_dict("records"):
            value = dict(row, count=part["component_count"])
            value["observation_id"] = part["released_count_id"]
            for attribute in ("age", "sex", "plumage"):
                value[attribute] = part[attribute] or pd.NA
            field = "details" if row["sheet"] == "2017-2021" else "detail"
            _, context = split_daily_context(row.get(field))
            value[field] = (
                "\n\n".join(text for text in (part["residual"], context) if text) or pd.NA
            )
            rows.append(dict(value, _position=position))
    parts = pd.DataFrame(rows, columns=[*observations.columns, "_position"])
    kept = observations.loc[~split].assign(_position=observations.index[~split])
    return (
        pd.concat([kept, parts], ignore_index=True)
        .sort_values("_position", kind="stable")
        .drop(columns="_position")
        .reset_index(drop=True)
    )
