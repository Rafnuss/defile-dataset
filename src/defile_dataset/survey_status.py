"""Trektellen survey status from native headers, DEFILE tags and reviewed decisions.

Every header is a complete survey (`survey_complete`) unless a decision says otherwise: weather
that made counting impossible is still complete (no bird passes) and flagged `weather_stop`; an
absence is cut out of the header; `survey_complete = false` only when birds are known to have
passed uncounted. See docs/survey-coverage.md.
"""

import html
import re
import shlex
from pathlib import Path

import pandas as pd

FIELDS = ["survey_complete", "weather_stop", "survey_comment"]
REVIEW_COLUMNS = ["survey_id", "date", "issue", "detail", "weather", "remarks"]
# `effect`: `weather` (a weather-stop row replaces the interval) or `absent` (the interval is cut).
INTERRUPTION_COLUMNS = [
    "interruption_id",
    "datetime",
    "time_precision",
    "effect",
    "note",
    "native_survey_id",
    "scope",
]
FLAGS = {"weather", "absent", "incomplete"}
# Tags written before 2026-10-09 (`survey_coverage=... reason=...`) are still read.
LEGACY = {
    "survey_coverage": {"complete", "partial", "none", "unknown"},
    "reason": {"weather", "no_observer", "logistics", "other", "unknown"},
}
ABSENCE_REASONS = {"no_observer", "logistics"}
HP_TEXT = r"\bHP\b|hors.?protocole|arrêt|arret|pas de spot|aucun oiseau|aucune visibilité|impossible|pas de comptage"


def parse_tag(body):
    """One DEFILE tag -> `(action, from, to)`.

    Actions: `weather` (counting impossible, no bird passed), `absent` (nobody counting: cut, or
    `remove` for a whole header), `incomplete` (birds passed uncounted) and `complete` (the
    default, stated explicitly).
    """
    tokens = shlex.split(body)
    flags = {t for t in tokens if "=" not in t}
    tag = dict(t.split("=", 1) for t in tokens if "=" in t)
    assert flags <= FLAGS and len(flags) <= 1
    assert set(tag) <= set(LEGACY) | {"from", "to"}
    assert all(tag[f] in values for f, values in LEGACY.items() if f in tag)
    assert ("from" in tag) == ("to" in tag)
    if flags:
        assert "survey_coverage" not in tag
        action = flags.pop()
    elif tag["survey_coverage"] == "none":
        action = "absent" if tag.get("reason") in ABSENCE_REASONS else "weather"
    else:
        action = {"complete": "complete", "partial": "complete", "unknown": "incomplete"}[
            tag["survey_coverage"]
        ]
    if "from" in tag:
        assert action in {"weather", "absent"}
    elif action == "absent":
        action = "remove"
    return action, tag.get("from"), tag.get("to")


def complete_by_default(surveys):
    """`surveys` with `FIELDS`, blanks read as complete and not a weather stop."""
    surveys = surveys.copy()
    for field in FIELDS:
        if field not in surveys:
            surveys[field] = pd.NA
    for field, default in (("survey_complete", True), ("weather_stop", False)):
        surveys[field] = (
            surveys[field]
            .map(
                lambda v: default
                if pd.isna(v) or v == ""
                else str(v).strip().lower() in {"true", "1", "1.0"}
            )
            .astype(bool)
        )
    return surveys


def release_status(survey):
    """`survey` as released: `survey_complete` `true`/`false`, `weather_stop` `true` or blank."""
    survey = survey.copy()
    survey["survey_complete"] = survey.survey_complete.map({True: "true", False: "false"})
    survey["weather_stop"] = survey.weather_stop.map({True: "true", False: pd.NA})
    return survey


def reviewed_action(row):
    """A row of the reviewed CSV -> its action (as `parse_tag`).

    A row with `datetime` is a timed weather stop (`weather_stop = true`) or absence; a row
    without applies to the whole header: `weather_stop = true`, `survey_complete = false`, or
    `survey_complete = remove` (an empty header that was no survey).
    """
    weather = str(row["weather_stop"]).strip().lower()
    complete = str(row["survey_complete"]).strip().lower()
    assert weather in {"", "true"}, f'{row["decision_id"]}: weather_stop {weather!r}'
    assert complete in {
        "",
        "false",
        "remove",
    }, f'{row["decision_id"]}: survey_complete {complete!r}'
    assert not (
        row["datetime"] and complete
    ), f'{row["decision_id"]}: a timed row is a weather stop or an absence'
    weather = weather == "true"
    if row["datetime"]:
        return "weather" if weather else "absent"
    if weather:
        return "weather"
    return {"false": "incomplete", "remove": "remove"}.get(complete, "complete")


def classify_trektellen(surveys, observations, reviewed):
    """Set `FIELDS` on each Trektellen header and list its timed weather stops and absences.

    Bird records and native survey times are not changed here: `integrate_interruptions` splits
    the headers afterwards. Decisions on a header with a problem (changed source text, malformed
    or conflicting tags) are withheld: it stays complete and is listed for review. Returns
    `(surveys, intervals, review)`.
    """
    surveys = complete_by_default(surveys)
    removed = pd.Series(False, index=surveys.index)
    birds = observations.loc[observations.taxon_kind.eq("bird")]
    bird_groups = dict(tuple(birds.groupby("survey_id", sort=False)))
    native = surveys.loc[surveys.source.eq("trektellen")]
    findings, intervals = [], []
    for sid in sorted(set("T" + reviewed.count_id.astype(str)) - set(native.survey_id)):
        findings.append(
            dict(
                survey_id=sid,
                issue="reviewed_header_missing",
                detail="Reviewed count ID absent from exports.",
            )
        )
    for i, row in native.iterrows():
        text = html.unescape(str(row.remarks)) if pd.notna(row.remarks) else ""
        weather = html.unescape(str(row.weather)) if pd.notna(row.weather) else ""
        problems, decisions = [], []
        for d in reviewed.loc[
            reviewed.count_id.astype(str).eq(str(int(row.trektellen_count_id)))
        ].to_dict("records"):
            if d["native_weather"] != weather or d["native_remarks"] != text:
                problems.append(("reviewed_source_changed", d["decision_id"]))
            decisions.append(
                dict(
                    id=d["decision_id"],
                    action=reviewed_action(d),
                    datetime=d["datetime"],
                    scope=d["scope"],
                    time_precision=d["time_precision"],
                    comment=d["survey_comment"],
                )
            )
        if text.count("[DEFILE") != len(re.findall(r"\[DEFILE\s+[^\]]*\]", text)):
            problems.append(("invalid_status_tag", "Malformed DEFILE tag."))
        for number, match in enumerate(re.finditer(r"\[DEFILE\s+([^\]]*)\]", text), 1):
            try:
                action, begin, end = parse_tag(match[1])
                interval = ""
                if begin:
                    date = pd.Timestamp(row.start).tz_convert("Europe/Paris").strftime("%Y-%m-%d")
                    begin, end = [
                        pd.Timestamp(date + " " + t).tz_localize("Europe/Paris")
                        for t in (begin, end)
                    ]
                    assert row.start <= begin < end <= row.end
                    interval = begin.isoformat() + "/" + end.isoformat()
                decisions.append(
                    dict(
                        id=f"{row.survey_id}-tag{number}",
                        action=action,
                        datetime=interval,
                        scope="interval" if interval else "period",
                        time_precision="clock",
                        comment="DEFILE tag in the remark.",
                    )
                )
            except (ValueError, AssertionError, TypeError, KeyError):
                problems.append(("invalid_status_tag", match[0]))
        if len({d["action"] for d in decisions if not d["datetime"]}) > 1:
            problems.append(("conflicting_classification", "Whole-header decisions disagree."))
        if problems:
            decisions = []
        comments = [
            d["comment"] for d in decisions if d["comment"] and not d["datetime"]
        ]  # timed ones go on their own row
        if comments:
            surveys.loc[i, "survey_comment"] = " | ".join(dict.fromkeys(comments))
        entries = bird_groups.get(row.survey_id, birds.iloc[:0])
        for d in decisions:
            if d["datetime"]:
                begin, end = [pd.Timestamp(t).tz_convert("UTC") for t in d["datetime"].split("/")]
                times = pd.to_datetime(entries.datetime, utc=True)
                if times.isna().any():
                    problems.append(
                        (
                            "untimed_birds_near_interruption",
                            "Untimed birds cannot be placed before or after the interruption.",
                        )
                    )
                covers = begin <= row.start and row.end <= end
                if ((times >= begin) & (times < end)).any() or (covers and len(entries)):
                    # As for a whole header: birds recorded in it, so it stays counted.
                    problems.append(
                        (
                            "birds_in_interruption",
                            f'Birds recorded in the {d["action"]} interval; withheld, kept as counted.',
                        )
                    )
                    continue
                intervals.append(
                    dict(
                        interruption_id=d["id"],
                        datetime=d["datetime"],
                        time_precision=d["time_precision"],
                        effect=d["action"],
                        note=d["comment"],
                        native_survey_id=row.survey_id,
                        scope=d["scope"],
                    )
                )
            elif d["action"] == "weather":
                surveys.loc[i, "weather_stop"] = True
            elif d["action"] == "incomplete":
                surveys.loc[i, "survey_complete"] = False
            elif d["action"] == "remove":
                removed[i] = True
        if not decisions and re.search(HP_TEXT, weather + " " + text, re.I):
            problems.append(
                ("ambiguous_status_text", "Review the remark for weather stops or absences.")
            )
        positive = entries["count"].fillna(0).gt(0)
        for field in ("direction2", "local"):
            if field in entries:
                positive |= entries[field].fillna(0).gt(0)
        if "estimation" in entries:
            positive |= entries.estimation.eq("x")
        if surveys.loc[i, "weather_stop"] and positive.any():
            surveys.loc[i, "weather_stop"] = False
            problems.append(
                (
                    "birds_in_weather_stop",
                    "Birds counted during a whole-header weather stop; kept as counted.",
                )
            )
        if removed[i] and len(entries):
            removed[i] = False
            problems.append(("removal_with_birds", "A header with bird records is never removed."))
        if not surveys.loc[i, "survey_complete"]:
            comment = surveys.loc[i, "survey_comment"]
            problems.append(
                (
                    "incomplete_survey",
                    comment if pd.notna(comment) else "Birds passed uncounted; no comment.",
                )
            )
        if not removed[i] and (pd.isna(row.start_original) or pd.isna(row.end_original)):
            problems.append(
                (
                    "missing_survey_hours",
                    "Original survey hours missing; calendar bounds are not effort.",
                )
            )
        for issue, detail in problems:
            findings.append(
                dict(
                    survey_id=row.survey_id,
                    date=row.date,
                    issue=issue,
                    detail=detail,
                    weather=row.weather,
                    remarks=row.remarks,
                )
            )
    surveys = surveys.loc[~removed]
    review = pd.DataFrame(findings, columns=REVIEW_COLUMNS)
    review = review.merge(surveys[["survey_id", "start", "end"]], on="survey_id", how="left")
    review["duration_hours"] = (review.end - review.start).dt.total_seconds() / 3600
    return surveys, pd.DataFrame(intervals, columns=INTERRUPTION_COLUMNS), review


def read_reviewed_status(root):
    return pd.read_csv(
        Path(root) / "config/survey-status/trektellen-survey-status.csv",
        keep_default_na=False,
        dtype={"count_id": str},
    )
