"""Apply owner-reviewed historical identification phrases to released main counts."""

import pandas as pd

from defile_dataset.attributes import split_daily_context
from defile_dataset.taxonomy_text import normalize_text, taxon_phrase


def refine_taxonomy(normal, rules):
    """Preserve lineage and quantities; never cross-assign independently described subgroups."""
    normal = normal.copy()
    normal["taxon_id"] = normal.get("taxon_id", normal.avibase_id)
    matches = {}
    for _, rule in rules.loc[rules.decision.eq("approve")].iterrows():
        candidates = normal.source.eq("historical") & normal.taxon_name_original.eq(
            rule.source_taxon
        )
        for i in normal.index[candidates & normal[rule.source_field].notna()]:
            head, _ = split_daily_context(normal.at[i, rule.source_field])
            if normalize_text(head) == normalize_text(rule.source_text):
                matches.setdefault(normal.at[i, "source_count_id"], []).append(rule.to_dict())
    additions, removed, audit = [], [], []
    for source_id, matched in matches.items():
        rows = normal.loc[normal.source_count_id.eq(source_id)]
        unique = pd.DataFrame(matched).drop_duplicates("review_id")
        row = rows.iloc[0]
        rule = unique.iloc[0]
        _, quantity, _ = taxon_phrase(rule.source_text)
        total = rows["count"].sum()
        quantity = quantity if rule.scope == "subset_requires_split" else total
        status = "applied"
        if unique.target_taxon_id.nunique() > 1:
            status = "conflicting_taxonomy_rules"
        elif quantity > total:
            status = "quantity_exceeds_source"
        elif quantity < total and rule.target_taxon_id != row.taxon_id:
            fields = ["age", "sex", "plumage", "datetime", "detail", "details"]
            if len(rows.reindex(columns=fields).fillna("").drop_duplicates()) > 1:
                status = "unassociated_attribute_or_time_subgroups"
        note = f"Reviewed taxonomy {rule.review_group}: {row.taxon_id} -> {rule.target_taxon_id}."
        if status != "applied":
            note += f" Unapplied: {status}; original wording and identification retained."
            indexes = rows.index
            for i in indexes:
                old = normal.at[i, "remark_processing"]
                normal.at[i, "remark_processing"] = (
                    str(old) + " " if pd.notna(old) else ""
                ) + note
            outputs = rows.to_dict("records")
        else:
            changed = row.taxon_id != rule.target_taxon_id
            outputs = rows.to_dict("records")
            if quantity < total and changed:
                outputs = [
                    dict(
                        row,
                        count=quantity,
                        taxon_id=rule.target_taxon_id,
                        observation_id=source_id + "-tax1",
                    ),
                    dict(row, count=total - quantity, observation_id=source_id + "-tax2"),
                ]
            elif changed:
                outputs = [
                    dict(
                        value,
                        taxon_id=rule.target_taxon_id,
                        observation_id=value["observation_id"] + "-tax1",
                    )
                    for value in outputs
                ]
            for value in outputs:
                for _, applied in unique.iterrows():
                    if applied.consume_text:
                        field = applied.source_field
                        if field + "_residual" in value:
                            field += "_residual"
                        _, context = split_daily_context(value.get(field))
                        value[field] = context or pd.NA
                old = value.get("remark_processing")
                value["remark_processing"] = (str(old) + " " if pd.notna(old) else "") + note
            removed.extend(rows.index)
            additions.extend(outputs)
        for value in outputs:
            audit.append(
                dict(
                    review_group=rule.review_group,
                    source_count_id=source_id,
                    observation_id=value["observation_id"],
                    original_taxon_id=row.taxon_id,
                    released_taxon_id=value.get("taxon_id", row.taxon_id),
                    count=value["count"],
                    source_field=rule.source_field,
                    source_text=rule.source_text,
                    text_consumed=bool(status == "applied" and rule.consume_text),
                    status=status,
                )
            )
    if additions:
        normal = pd.concat(
            [normal.drop(index=removed), pd.DataFrame(additions)], ignore_index=True
        )
    return normal, pd.DataFrame(
        audit,
        columns=[
            "review_group",
            "source_count_id",
            "observation_id",
            "original_taxon_id",
            "released_taxon_id",
            "count",
            "source_field",
            "source_text",
            "text_consumed",
            "status",
        ],
    )
