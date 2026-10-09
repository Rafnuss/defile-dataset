"""Apply accepted record-level timing decisions while preserving original source fields."""

import pandas as pd

from defile_dataset.build import add_flag


def reviewed_entry_times(observations, surveys, decisions):
    """Return corrected observations and a before/after audit; never change bird quantities.

    Clear leaves a linked count without its own clock so its survey is the fallback.
    Intervals bound the observation, not counting effort; native survey bounds are unchanged.
    """
    assert decisions.observation_id.is_unique, "Timing decisions must have unique observation IDs."
    assert decisions.observation_id.isin(
        observations.observation_id
    ).all(), "Timing review refers to missing source records."
    assert decisions.action.isin(["clear", "point", "interval"]).all()
    assert (
        decisions.survey_id.eq("").all()
        or decisions.loc[decisions.survey_id.ne(""), "survey_id"].isin(surveys.survey_id).all()
    )
    rows = observations.copy()
    rules = decisions.set_index("observation_id").reindex(rows.observation_id).set_axis(rows.index)
    selected = rules.action.notna()
    assert rows.loc[selected, "date"].dt.strftime("%Y-%m-%d").eq(rules.loc[selected, "date"]).all()
    audit = rows.loc[
        selected,
        [
            "observation_id",
            "survey_id",
            "date",
            "source",
            "taxon_name_original",
            "count",
            "direction2",
            "local",
            "datetime_original",
            "datetime",
            "time_resolution",
            "flags",
        ],
    ].copy()
    audit = audit.rename(
        columns={
            "survey_id": "survey_id_before",
            "datetime": "datetime_before",
            "time_resolution": "time_resolution_before",
            "flags": "flags_before",
        }
    )
    rows["survey_id_original"] = rows.survey_id
    rows["datetime_interval"] = pd.Series(pd.NA, index=rows.index, dtype="string")
    rows["timing_review_action"] = rules.action
    rows["timing_review_reason"] = rules.reason
    rows.loc[selected, "datetime"] = pd.NaT
    rows.loc[selected, "time_resolution"] = "interval"
    relink = selected & rules.survey_id.ne("")
    rows.loc[relink, "survey_id"] = rules.loc[relink, "survey_id"]
    point = rules.action.eq("point")
    rows.loc[point, "datetime"] = pd.to_datetime(rules.loc[point, "datetime"], utc=True)
    rows.loc[point, "time_resolution"] = "point"
    interval = rules.action.eq("interval")
    start = pd.to_datetime(rules.loc[interval, "interval_start"], utc=True)
    end = pd.to_datetime(rules.loc[interval, "interval_end"], utc=True)
    assert start.lt(end).all(), "Reviewed intervals must have increasing bounds."
    rows.loc[interval, "datetime_interval"] = (
        rules.loc[interval, "interval_start"] + "/" + rules.loc[interval, "interval_end"]
    )
    for action in ["clear", "point", "interval"]:
        add_flag(rows, rules.action.eq(action), "reviewed_time_" + action)
    add_flag(rows, relink, "reviewed_survey_link")
    # Resolved source mismatches must not keep a stale day-fallback processing note.
    resolved = point | interval
    rows.loc[resolved, "flags"] = (
        rows.loc[resolved, "flags"]
        .str.replace(r"(^|;)time_outside_survey(?=;|$)", "", regex=True)
        .str.strip(";")
    )
    old_notes = rows.reindex(columns=["remark_processing"]).remark_processing.fillna("")
    rows.loc[selected, "remark_processing"] = (
        old_notes.loc[selected] + " Reviewed timing: " + rules.loc[selected, "reason"]
    ).str.strip()
    for field in ["comment", "remark"]:
        # Keep original timing wording even when it disagrees with an accepted review.
        rows.loc[selected, field + "_residual"] = rows.loc[selected, field]
    for field in ["survey_id", "datetime", "datetime_interval", "time_resolution", "flags"]:
        audit[field + "_after"] = rows.loc[selected, field]
    audit[["action", "reason", "evidence"]] = rules.loc[selected, ["action", "reason", "evidence"]]
    return rows, audit.reset_index(drop=True)
