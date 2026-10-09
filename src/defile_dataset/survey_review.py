"""Evidence-based survey interruptions and coverage review."""

import json
from pathlib import Path

import pandas as pd

from defile_dataset.consolidate import ERA, local_dates

EMPTY_HOUR_NOTE = "hour inside the declared day window with no record: counted, nothing seen"


def _iso(t):
    return t.isoformat().replace("+00:00", "Z")


def _periods(table):
    """`table` with `date` (local), `start` and `end` (UTC) from its `datetime` interval."""
    return table.assign(
        date=local_dates(table.datetime),
        start=pd.to_datetime(table.datetime.str.split("/").str[0], utc=True, format="ISO8601"),
        end=pd.to_datetime(table.datetime.str.split("/").str[1], utc=True, format="ISO8601"),
    )


def integrate_historical_gaps(survey, historical, breaks, count=None):
    """Subtract the union of released periods from each declared historical day window.

    Released periods are the surveys and the counts' own time ranges (a count timed over a range
    shows someone counting then). What remains is added as complete empty intervals (`status`
    `added`), except where `breaks` (config/audit-settings/historical-gap-breaks.csv) documents an
    absence: that time is cut, no row (`cut`).
    """
    periods = _periods(survey)[["date", "start", "end"]]
    if count is not None:
        ranged = count.loc[count.datetime.fillna("").str.contains("T.*/", regex=True)]
        periods = pd.concat([periods, _periods(ranged)[["date", "start", "end"]]])
    days = dict(tuple(periods.groupby("date")))
    rows, audit = [], []
    for (sheet, date), day in historical.groupby(["sheet", "date"], sort=True):
        begin, end = day.day_start.min(), day.day_end.max()
        gaps, cursor = [], begin
        native = days.get(date.strftime("%Y-%m-%d"), periods.iloc[:0])
        for start, stop in native.sort_values("start")[["start", "end"]].itertuples(
            index=False, name=None
        ):
            if cursor < min(start, end):
                gaps.append((cursor, min(start, end)))
            cursor = max(cursor, stop)
        if cursor < end:
            gaps.append((cursor, end))
        for left, right in gaps:
            boundaries = {left, right}
            reviewed = breaks.loc[breaks.date.eq(date.strftime("%Y-%m-%d"))]
            for item in reviewed.itertuples(index=False):
                start, stop = [pd.Timestamp(t).tz_convert("UTC") for t in item.datetime.split("/")]
                boundaries.update(t for t in (start, stop) if left < t < right)
            boundaries = sorted(boundaries)
            for start, stop in zip(boundaries, boundaries[1:]):
                hours = (stop - start).total_seconds() / 3600
                status = "added"
                note = (
                    "Minute-scale boundary gap between recorded periods; exact times retained, continuous effort assumed."
                    if hours <= 1 / 60
                    else "Empty interval inferred from the declared day window and omitted empty-hour recording convention; attendance not independently verified."
                )
                if hours >= 3:
                    note += " Long gap reviewed against available workbook notes; no timed interruption documented."
                for item in reviewed.itertuples(index=False):
                    break_start, break_end = [
                        pd.Timestamp(t).tz_convert("UTC") for t in item.datetime.split("/")
                    ]
                    if break_start <= start and stop <= break_end:
                        status, note = "cut", item.note
                source_id = (
                    f'H{date:%Y%m%d}-{start.tz_convert("Europe/Paris"):%H%M%S}-declared-gap'
                )
                interval = _iso(start) + "/" + _iso(stop)
                if status == "added":
                    rows.append(
                        dict(
                            survey_id=source_id,
                            datetime=interval,
                            recording_era=ERA[sheet],
                            survey_complete=True,
                            weather_stop=False,
                            survey_comment=note,
                            remark_processing=EMPTY_HOUR_NOTE,
                        )
                    )
                audit.append(
                    dict(
                        source_survey_id=source_id,
                        sheet=sheet,
                        date=date.strftime("%Y-%m-%d"),
                        datetime=interval,
                        day_start=begin,
                        day_end=end,
                        hours=(stop - start).total_seconds() / 3600,
                        status=status,
                        note=note,
                    )
                )
    return pd.concat(
        [survey, pd.DataFrame(rows).reindex(columns=survey.columns)], ignore_index=True
    ), pd.DataFrame(audit)


def empty_survey_review(survey, count, observations, gaps):
    """Document all released periods without bird rows, independently of coverage."""
    rows = survey.loc[~survey.survey_id.isin(count.survey_id)].copy()
    rows["date"] = local_dates(rows.datetime)
    rows["duration_hours"] = (
        pd.to_datetime(rows.datetime.str.split("/").str[1], utc=True)
        - pd.to_datetime(rows.datetime.str.split("/").str[0], utc=True)
    ).dt.total_seconds() / 3600
    rows["no_species_entries"] = (
        rows.source_survey_id.map(
            observations.loc[observations.taxon_kind.eq("no_species")].groupby("survey_id").size()
        )
        .fillna(0)
        .astype(int)
    )
    rows["review_class"] = "empty_native_header"
    rows.loc[rows.no_species_entries.gt(0), "review_class"] = "explicit_no_species"
    rows.loc[
        rows.source_survey_id.isin(gaps.source_survey_id), "review_class"
    ] = "declared_empty_interval"
    rows.loc[
        rows.source_survey_id.isin(gaps.source_survey_id) & rows.duration_hours.le(1 / 60),
        "review_class",
    ] = "minute_boundary_gap"
    rows.loc[
        rows.source_survey_id.isin(gaps.source_survey_id) & rows.duration_hours.ge(3),
        "review_class",
    ] = "long_declared_gap"
    rows.loc[rows.weather_stop.fillna(False).astype(bool), "review_class"] = "weather_stop"
    rows.loc[~rows.survey_complete.fillna(True).astype(bool), "review_class"] = "incomplete"
    missing_counts = rows.survey_comment.fillna("").str.contains(
        r"missing count data|counts? (?:were )?deleted", case=False
    )
    missing_counts |= rows.remark_processing.fillna("").str.contains("entries were deleted")
    rows.loc[missing_counts, "review_class"] = "missing_count_data"
    bird_dates = set(
        local_dates(
            count.datetime.fillna(count.survey_id.map(survey.set_index("survey_id").datetime))
        )
    )
    rows["day_has_released_birds"] = rows.date.isin(bird_dates)
    return rows[
        [
            "survey_id",
            "source_survey_id",
            "date",
            "datetime",
            "duration_hours",
            "recording_era",
            "survey_complete",
            "weather_stop",
            "survey_comment",
            "review_class",
            "day_has_released_birds",
            "no_species_entries",
            "observers",
            "weather",
            "remark",
            "remark_processing",
        ]
    ].sort_values(["date", "datetime", "survey_id"])


def validate_historical_gaps(survey, count, gaps):
    """Check final gap rows against their declared bounds, other surveys and count links."""
    from defile_dataset.checks import Check

    gaps = gaps.loc[gaps.status.eq("added")]
    periods = _periods(survey)
    added = periods.loc[periods.survey_id.isin(gaps.survey_id)].merge(
        gaps[["survey_id", "day_start", "day_end"]], on="survey_id", validate="one_to_one"
    )
    outside = added.loc[
        (added.start < added.day_start) | (added.end > added.day_end) | (added.start >= added.end)
    ]
    pairs = added[["survey_id", "date", "start", "end"]].merge(
        periods[["survey_id", "date", "start", "end"]], on="date", suffixes=("", "_other")
    )
    overlaps = pairs.loc[
        pairs.survey_id.ne(pairs.survey_id_other)
        & (pairs.start < pairs.end_other)
        & (pairs.end > pairs.start_other)
    ]
    linked = count.loc[count.survey_id.isin(gaps.survey_id)]
    # A count timed inside an "empty" gap contradicts it, whichever survey it is linked to.
    timed = count.loc[count.datetime.fillna("").str.contains("T")]
    timed = timed.assign(
        datetime=timed.datetime.where(
            timed.datetime.str.contains("/"), timed.datetime + "/" + timed.datetime
        )
    )
    clocks = _periods(timed)[["count_id", "date", "start", "end"]].merge(
        added[["survey_id", "date", "start", "end"]], on="date", suffixes=("", "_gap")
    )
    inside = clocks.loc[
        (clocks.start < clocks.end_gap)
        & (
            (clocks.end > clocks.start_gap)
            | (clocks.start.eq(clocks.end) & clocks.start.ge(clocks.start_gap))
        )
    ]
    linked = pd.concat([linked, count.loc[count.count_id.isin(inside.count_id)]]).drop_duplicates(
        "count_id"
    )
    return [
        Check(
            "Historical effort gaps inside declared windows",
            "fail" if len(outside) else "pass",
            f"{len(outside)} gaps outside their day window.",
            outside,
        ),
        Check(
            "Historical effort gaps do not overlap surveys",
            "fail" if len(overlaps) else "pass",
            f"{len(overlaps)} overlapping gap/survey pairs.",
            overlaps,
        ),
        Check(
            "Historical effort gaps have no counts",
            "fail" if len(linked) else "pass",
            f"{len(linked)} count rows linked to, or timed inside, added gaps.",
            linked,
        ),
    ]


def validate_survey_rows(survey, count):
    """Final survey table: weather stops hold no bird, and no two survey rows overlap."""
    from defile_dataset.checks import Check

    stops = survey.survey_id.loc[
        survey.weather_stop.astype("string").str.lower().eq("true").fillna(False)
    ]
    in_stops = count.loc[count.survey_id.isin(stops)]
    periods = _periods(survey).sort_values(["start", "end"])
    previous_end = periods.end.cummax().shift()
    overlaps = periods.loc[periods.start < previous_end, ["survey_id", "datetime"]]
    return [
        Check(
            "Weather stops hold no counts",
            "fail" if len(in_stops) else "pass",
            f"{len(in_stops)} count rows linked to a weather stop.",
            in_stops,
        ),
        Check(
            "Released surveys do not overlap",
            "fail" if len(overlaps) else "pass",
            f"{len(overlaps)} survey rows starting before an earlier one ends.",
            overlaps,
        ),
    ]


def _weather_stop(row, note):
    row = row.copy()
    row["survey_complete"], row["weather_stop"] = True, True
    row["survey_comment"] = note or pd.NA
    return row


def integrate_interruptions(survey, count, status_intervals=None):
    """Apply timed weather stops and absences to the survey rows; returns `(survey, count, intervals)`.

    Every survey overlapping an interval is cut around it. A weather stop then becomes its own
    complete row flagged `weather_stop` (a copy of the survey it interrupts, or a curated row when
    it lies outside any survey); an absence leaves no row. Counts of a cut survey move to the piece
    holding their own time (the nearest piece if none does); those without a time of their own
    keep the day only (date-only `datetime`), so they never inherit a narrower piece.
    """
    from defile_dataset.survey_status import INTERRUPTION_COLUMNS, complete_by_default

    interruptions = (
        status_intervals.fillna("").copy()
        if status_intervals is not None
        else pd.DataFrame(columns=INTERRUPTION_COLUMNS)
    )
    survey, count = complete_by_default(survey), count.copy()
    for row in interruptions.itertuples(index=False):
        begin, end = [pd.Timestamp(t).tz_convert("UTC") for t in row.datetime.split("/")]
        date = begin.tz_convert("Europe/Paris").strftime("%Y-%m-%d")
        starts = pd.to_datetime(survey.datetime.str.split("/").str[0], utc=True, format="ISO8601")
        ends = pd.to_datetime(survey.datetime.str.split("/").str[1], utc=True, format="ISO8601")
        hit = survey.index[(starts < end) & (ends > begin)]
        added = []
        for i in hit:
            sid, a, b = survey.loc[i, "survey_id"], starts[i], ends[i]
            spans = [(a, min(b, begin))] * (a < begin) + [(max(a, end), b)] * (b > end)
            pieces = []
            for n, (left, right) in enumerate(spans):
                piece = survey.loc[i].copy()
                piece["survey_id"] = sid if n == 0 else f"{sid}-part{n + 1}"
                piece["datetime"] = _iso(left) + "/" + _iso(right)
                pieces.append(piece)
            if row.effect == "weather":
                stop = survey.loc[i].copy()
                stop["survey_id"] = f"{sid}-weather" if spans else sid
                stop["datetime"] = _iso(max(a, begin)) + "/" + _iso(min(b, end))
                pieces.append(_weather_stop(stop, row.note))
            if not pieces:  # an absence over a whole survey: keep it rather than orphan its counts
                continue
            spans = [
                tuple(pd.Timestamp(t).tz_convert("UTC") for t in p["datetime"].split("/"))
                for p in pieces
            ]
            linked = count.index[count.survey_id.eq(sid)]
            own = count.loc[linked, "datetime"].astype("string")
            timed = own.str.contains("T", na=False)
            when = pd.to_datetime(
                own.where(timed).str.split("/").str[0], utc=True, format="ISO8601"
            )
            for j in linked[timed.to_numpy()]:
                t = when[j]
                inside = [k for k, (left, right) in enumerate(spans) if left <= t <= right]
                nearest = min(
                    range(len(spans)),
                    key=lambda k: min(abs(t - spans[k][0]), abs(t - spans[k][1])),
                )
                count.loc[j, "survey_id"] = pieces[inside[0] if inside else nearest]["survey_id"]
            untimed = linked[~timed.to_numpy()]
            count.loc[untimed, "datetime"] = count.loc[untimed, "datetime"].fillna(date)
            count.loc[untimed, "survey_id"] = pieces[0]["survey_id"]
            survey = survey.drop(index=i)
            added += pieces
        # The rest of a weather stop, outside every survey, is a curated row; a calendar-day
        # stop over a day that has a survey needs no padding.
        if row.effect == "weather" and not (row.scope == "day" and len(hit)):
            rest = [(begin, end)]
            for i in hit:
                rest = [
                    piece
                    for left, right in rest
                    for piece in (
                        [(left, min(right, starts[i]))] * (left < starts[i])
                        + [(max(left, ends[i]), right)] * (right > ends[i])
                    )
                    if piece[0] < piece[1]
                ]
            for n, (left, right) in enumerate(rest, 1):
                stop = pd.Series(
                    dict(
                        survey_id=f"{row.interruption_id}-weather" + (str(n) if n > 1 else ""),
                        datetime=_iso(left) + "/" + _iso(right),
                        recording_era="curated",
                        remark_processing="Weather stop documented outside any native survey.",
                    )
                )
                added.append(_weather_stop(stop, row.note))
        survey = pd.concat(
            [survey, pd.DataFrame(added).reindex(columns=survey.columns)], ignore_index=True
        )
    survey = complete_by_default(survey)
    return survey, count, interruptions


def observed_hours(survey):
    """Hours counted (union of complete, non-weather-stop rows); unknown if any row is incomplete."""
    if "survey_complete" in survey and (~survey.survey_complete.fillna(True).astype(bool)).any():
        return float("nan")
    counted = survey
    if "weather_stop" in survey:
        counted = survey.loc[~survey.weather_stop.fillna(False).astype(bool)]
    hours, last = 0, None
    for start, end in sorted(zip(counted.start, counted.end)):
        hours += max(
            0, (end - max(start, last if last is not None else start)).total_seconds() / 3600
        )
        last = max(end, last if last is not None else end)
    return hours


def interruption_review(survey, observations, root):
    """Review gaps/short days without converting ambiguous absences into weather closures."""
    windows = pd.read_csv(Path(root) / "config/audit-settings/report-season-windows.csv")
    native = survey.loc[~survey.recording_era.eq("curated")].copy()
    native["date"] = local_dates(native.datetime)
    starts = pd.to_datetime(native.datetime.str.split("/").str[0], utc=True, format="ISO8601")
    ends = pd.to_datetime(native.datetime.str.split("/").str[1], utc=True, format="ISO8601")
    native["start"], native["end"] = starts, ends
    native["hours"] = (ends - starts).dt.total_seconds() / 3600
    observed = observations.assign(date=observations.date.dt.strftime("%Y-%m-%d"))
    observation_days = dict(tuple(observed.groupby("date", sort=False)))
    review_notes = (
        pd.read_csv(Path(root) / "config/audit-settings/interruption-review-notes.csv")
        .set_index("date")
        .note.to_dict()
    )
    released_dates = local_dates(survey.datetime)
    rows = []
    for window in windows.itertuples(index=False):
        for date in pd.date_range(window.start, window.end).strftime("%Y-%m-%d"):
            day = native.loc[native.date.eq(date)]
            entries = observation_days.get(date, observed.iloc[:0])
            hours = observed_hours(day)
            short = pd.isna(hours) or (
                pd.notna(window.partial_threshold_hours) and hours < window.partial_threshold_hours
            )
            marker = entries.taxon_kind.eq("no_species").any()
            stopped, incomplete = day.weather_stop.fillna(False).astype(
                bool
            ), ~day.survey_complete.fillna(True).astype(bool)
            released = survey.loc[released_dates.eq(date)]
            if (
                day.empty
                or short
                or marker
                or stopped.any()
                or incomplete.any()
                or date in review_notes
            ):
                unresolved = released.empty or incomplete.any() or pd.isna(hours)
                resolved = (
                    released.weather_stop.fillna(False).astype(bool).any()
                    or marker
                    or released.recording_era.eq("curated").any()
                )
                rows.append(
                    dict(
                        date=date,
                        native_survey_ids=json.dumps(day.survey_id.tolist()),
                        native_hours=hours,
                        bird_rows=int(entries.taxon_kind.eq("bird").sum()),
                        bird_total=entries.loc[entries.taxon_kind.eq("bird"), "count"].sum(),
                        no_species_marker=bool(marker),
                        reported_closure_days=window.reported_closure_days,
                        partial_threshold_hours=window.partial_threshold_hours,
                        assessment="unresolved"
                        if unresolved or not resolved
                        else "linked_curated_evidence",
                        note=review_notes.get(
                            date,
                            " | ".join(day.survey_comment.dropna().unique())
                            or "Missing survey, short coverage or no-species marker alone does not establish a weather interruption.",
                        ),
                    )
                )
    return pd.DataFrame(rows)
