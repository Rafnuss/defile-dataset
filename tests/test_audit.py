"""Audit outcomes, component accounting and coverage must retain scientific meaning."""

import pandas as pd


def test_status_report_keeps_native_edit_link_with_readable_survey_id():
    from defile_dataset.checks import Check
    from defile_dataset.report import _check_section

    rows = pd.DataFrame(
        [dict(survey_id="T-20251020-0800", trektellen_count_id="3221751", date="2025-10-20")]
    )
    section = _check_section(
        Check("Status", "warn", "Review", rows, columns=("date", "survey_id"))
    )
    assert "count/edit/3221751" in section
    assert "count/edit/-20251020-0800" not in section
    assert "T-20251020-0800" in section


from defile_dataset.audit import count_outliers, daily_coverage, quantity_components, summarize
from defile_dataset.checks import Check


def test_count_outliers_rank_peaks_and_separate_taxa_seasons_and_categories():
    dates = pd.to_datetime(
        [f"{year}-09-{day:02}" for year in (2020, 2021) for day in range(1, 13)]
    )
    survey = pd.DataFrame(
        dict(
            survey_id=[f"S{i}" for i in range(24)],
            datetime=[f"{date:%Y-%m-%d}T06:00:00Z/{date:%Y-%m-%d}T07:00:00Z" for date in dates],
            survey_complete=True,
            weather_stop=False,
        )
    )
    count = pd.DataFrame(
        dict(
            count_id=[f"C{i}" for i in range(24)],
            survey_id=survey.survey_id,
            datetime=None,
            taxon_id="A",
            count_category="normal",
            count=[10] * 22 + [1000, 10000],
        )
    )
    extra = pd.DataFrame(
        [
            dict(
                count_id="split",
                survey_id="S0",
                datetime=None,
                taxon_id="A",
                count_category="normal",
                count=5,
            ),
            dict(
                count_id="presence",
                survey_id="S1",
                datetime=None,
                taxon_id="A",
                count_category="normal",
                count=pd.NA,
            ),
            dict(
                count_id="reverse",
                survey_id="S1",
                datetime=None,
                taxon_id="A",
                count_category="reverse",
                count=10000,
            ),
            dict(
                count_id="other",
                survey_id="S1",
                datetime=None,
                taxon_id="B",
                count_category="normal",
                count=10000,
            ),
            dict(
                count_id="month",
                survey_id=None,
                datetime="2020-10-01",
                taxon_id="A",
                count_category="normal",
                count=10000,
            ),
        ]
    )
    count = pd.concat([count, extra], ignore_index=True)
    count["remark"] = ""
    count.loc[count.count_id.eq("C0"), "remark"] = "énorme groupe !!!"
    survey["survey_comment"] = ""
    survey.loc[survey.survey_id.eq("S0"), "survey_comment"] = "Passage exceptionnel."
    survey["remark"] = ""
    survey.loc[survey.survey_id.eq("S0"), "remark"] = "Effort confirmé."
    original = count.copy(deep=True)
    taxonomy = pd.DataFrame(dict(taxon_id=["A", "B"], english_name=["Taxon A", "Taxon B"]))
    result = count_outliers(count, survey, taxonomy, daily_coverage(count, survey))
    peaks = result.loc[result.metric.eq("daily_count") & result.flagged]
    assert peaks.daily_count.tolist() == [10000]
    assert peaks.outlier_score.is_monotonic_decreasing
    assert peaks.reference_days.eq(23).all()
    assert peaks.reference_median.round(5).eq(10).all()
    assert peaks.outlier_score.tolist() == [10]
    smaller_peak = result.loc[result.metric.eq("daily_count") & result.daily_count.eq(1000)]
    assert smaller_peak.outlier_score.tolist() == [0.1]
    assert not smaller_peak.flagged.any()
    assert result.loc[result.reference_days.lt(20), "outlier_score"].isna().all()
    first = result.loc[result.metric.eq("daily_count") & result.date.eq(dates[0])].iloc[0]
    assert first.daily_count == 15 and first.count_ids == "C0|split"
    assert first.count_remarks == "C0: énorme groupe !!!"
    assert first.survey_comments == "S0: Passage exceptionnel."
    assert first.survey_remarks == "S0: Effort confirmé."
    assert "presence" not in "|".join(result.count_ids)
    pd.testing.assert_frame_equal(count, original)


def test_count_rates_use_union_effort_and_exclude_unknown_zero_and_unlinked_effort():
    dates = pd.to_datetime(
        [f"{year}-09-{day:02}" for year in (2020, 2021) for day in range(1, 16)]
    )
    survey = pd.DataFrame(
        dict(
            survey_id=[f"S{i}" for i in range(30)],
            datetime=[f"{date:%Y-%m-%d}T06:00:00Z/{date:%Y-%m-%d}T08:00:00Z" for date in dates],
            survey_complete=True,
            weather_stop=False,
        )
    )
    survey.loc[10, "datetime"] = "2020-09-11T06:00:00Z/2020-09-11T06:01:00Z"
    survey.loc[11, "survey_complete"] = False
    survey.loc[12, "weather_stop"] = True
    count = pd.DataFrame(
        dict(
            count_id=[f"C{i}" for i in range(30)],
            survey_id=survey.survey_id,
            datetime=None,
            taxon_id="A",
            count_category="normal",
            count=100,
        )
    )
    count.loc[13, ["survey_id", "datetime"]] = [None, "2020-09-14"]
    count.loc[14, "count"] = 0
    count = pd.concat(
        [
            count,
            pd.DataFrame(
                [
                    dict(
                        count_id="partial",
                        survey_id="S13",
                        datetime=None,
                        taxon_id="A",
                        count_category="normal",
                        count=1,
                    ),
                    dict(
                        count_id="presence",
                        survey_id=None,
                        datetime="2020-09-01",
                        taxon_id="A",
                        count_category="normal",
                        count=pd.NA,
                    ),
                ]
            ),
        ],
        ignore_index=True,
    )
    survey = pd.concat([survey, survey.iloc[[0]].assign(survey_id="overlap")], ignore_index=True)
    taxonomy = pd.DataFrame(dict(taxon_id=["A"], english_name=["Taxon A"]))
    result = count_outliers(count, survey, taxonomy, daily_coverage(count, survey))
    rates = result.loc[result.metric.eq("count_rate")].set_index("date")
    assert rates.loc[dates[0], "count_rate"] == 50  # Overlap is not double effort.
    assert rates.loc[dates[10], "count_rate"] == 6000
    assert rates.loc[dates[10], "flagged"]
    assert rates.loc[dates[11:14], "count_rate"].isna().all()
    assert rates.loc[dates[14], "count_rate"] == 0
    assert pd.isna(rates.loc[dates[14], "outlier_score"])
    assert rates.loc[rates.count_rate.gt(0), "reference_days"].eq(25).all()
    totals = result.loc[result.metric.eq("daily_count")]
    assert not totals.flagged.any()
    assert totals.loc[totals.daily_count.gt(0), "outlier_score"].notna().all()


def test_outlier_scores_are_relative_to_flocking_variability_and_ignore_zeros():
    dates = pd.date_range("2020-09-01", periods=26)
    survey = pd.DataFrame(
        dict(
            survey_id=[f"S{i}" for i in range(26)],
            datetime=[f"{day:%Y-%m-%d}T06:00:00Z/{day:%Y-%m-%d}T07:00:00Z" for day in dates],
            survey_complete=True,
            weather_stop=False,
        )
    )
    # Both species have the same relative variability, despite 1000-fold abundance.
    count = pd.concat(
        [
            pd.DataFrame(
                dict(
                    count_id=[f"{taxon}{i}" for i in range(26)],
                    survey_id=survey.survey_id,
                    datetime=None,
                    taxon_id=taxon,
                    count_category="normal",
                    count=[
                        value * scale
                        for value in [1, 2, 5, 10, 20, 50] * 2
                        + [100, 1000]
                        + [1, 2, 5, 10, 20, 50] * 2
                    ],
                )
            )
            for taxon, scale in (("A", 1), ("B", 1000))
        ],
        ignore_index=True,
    )
    # Zeros must not make ordinary flock sizes look extreme.
    zeros = count.iloc[:24].copy()
    zeros["count_id"] = "zero-" + zeros.count_id
    zeros["count"] = 0
    zeros["datetime"] = zeros.survey_id.str[1:].astype(int).map(lambda i: f"{1990+i}-09-14")
    zeros["survey_id"] = None
    count = pd.concat([count, zeros], ignore_index=True)
    taxonomy = pd.DataFrame(dict(taxon_id=["A", "B"], english_name=["Small", "Flocking"]))
    result = count_outliers(count, survey, taxonomy, daily_coverage(count, survey))
    totals = result.loc[result.metric.eq("daily_count")]
    ordinary = totals.loc[totals.date.eq(dates[12])].set_index("taxon_id")
    assert not ordinary.flagged.any()
    assert ordinary.loc["A", "outlier_score"] == ordinary.loc["B", "outlier_score"]
    extreme = totals.loc[totals.date.eq(dates[13])].set_index("taxon_id")
    assert extreme.flagged.all()
    assert extreme.loc["A", "outlier_score"] == extreme.loc["B", "outlier_score"]
    assert totals.loc[totals.date.eq(dates[0]), "outlier_score"].isna().all()
    assert totals.loc[totals.daily_count.eq(0), "outlier_score"].isna().all()


def test_seasonal_reference_crosses_new_year_and_excludes_candidate_and_summer():
    dates = pd.to_datetime(
        [f"{year}-12-31" for year in range(2000, 2021)] + ["2021-01-01", "2020-07-01"]
    )
    survey = pd.DataFrame(
        dict(
            survey_id=[f"S{i}" for i in range(len(dates))],
            datetime=[f"{day:%Y-%m-%d}T06:00:00Z/{day:%Y-%m-%d}T07:00:00Z" for day in dates],
            survey_complete=True,
            weather_stop=False,
        )
    )
    count = pd.DataFrame(
        dict(
            count_id=[f"C{i}" for i in range(len(dates))],
            survey_id=survey.survey_id,
            datetime=None,
            taxon_id="A",
            count_category="normal",
            count=[10] * 21 + [1000, 1000000000],
        )
    )
    taxonomy = pd.DataFrame(dict(taxon_id=["A"], english_name=["Taxon A"]))
    result = count_outliers(count, survey, taxonomy, daily_coverage(count, survey))
    candidate = result.loc[result.date.eq("2021-01-01") & result.metric.eq("daily_count")].iloc[0]
    assert candidate.reference_days == 21
    assert candidate.reference_p95 == candidate.reference_max == 10
    assert candidate.outlier_score == 100 and candidate.flagged
    assert result.loc[result.date.eq("2020-07-01"), "outlier_score"].isna().all()


def test_outlier_report_keeps_all_flagged_rows_in_score_order():
    from defile_dataset.report import render

    rows = pd.DataFrame(dict(outlier_score=[10.0, 5.0] + [4.0] * 210))
    check = Check(
        "Unusual daily counts",
        "warn",
        "",
        rows,
        key="daily-count-outliers",
        file="count_outliers.csv",
    )
    document = render([check], summarize([check]))
    assert document.count("<tr data-filter-value=") == 212
    assert document.index('data-sort="10.0"') < document.index('data-sort="5.0"')
    assert 'href="count_outliers.csv"' in document
    assert "Effectifs journaliers atypiques" in document
    assert summarize([check])["build_status"] == "passed"


def test_warning_is_independent_of_build_validity():
    assert summarize([Check("Daylight", "warn", "Inspect period")])["build_status"] == "passed"
    assert summarize([Check("Unique ids", "fail", "Duplicated")])["build_status"] == "blocked"


def test_season_coverage_information_does_not_request_corrections():
    from defile_dataset.report import render

    check = Check(
        "Coverage context within reported seasons",
        "info",
        "",
        pd.DataFrame({"date": ["2020-09-01"], "assessment": ["documented_incomplete"]}),
        key="season-coverage",
        group="Coverage and published totals",
    )
    document = render([check], summarize([check]))
    assert "information" in document and "documented_incomplete" in document
    assert "not warnings" in document
    assert "Missing or short coverage within reported seasons" not in document
    assert summarize([check])["build_status"] == "passed"


def test_quantity_components_show_remainder_and_conflict_without_changing_source():
    source = pd.DataFrame(
        [
            dict(
                observation_id="H1",
                date="2020-09-01",
                sheet="2017-2021",
                row=2,
                count=5,
                detail="1x mâle adulte / 2x femelle adulte",
                status="quantity_mismatch",
            ),
            dict(
                observation_id="H2",
                date="2020-09-02",
                sheet="2017-2021",
                row=3,
                count=2,
                detail="3x adulte",
                status="quantity_mismatch",
            ),
        ]
    )
    from pathlib import Path

    from defile_dataset.attributes import historical_attributes

    CROSSWALK = pd.read_csv(Path("config/attributes/historical_attributes.csv"), dtype=str)
    source["details"] = source.detail
    _, parsed = historical_attributes(source, CROSSWALK)
    original = source.copy(deep=True)
    rows = quantity_components(parsed)
    assert rows.loc[rows.observation_id.eq("H-2017-2021-r2"), "component_count"].tolist() == [
        1,
        2,
        2,
    ]
    assert rows.loc[rows.observation_id.eq("H-2017-2021-r3"), "source_minus_detail"].tolist() == [
        -1
    ]
    assert (rows.component_count >= 0).all()
    pd.testing.assert_frame_equal(source, original)


def test_final_daily_coverage_merges_periods_and_leaves_weather_stops_out_of_hours():
    start = pd.Timestamp("2020-09-01T06:00:00Z")
    survey = pd.DataFrame(
        dict(
            survey_id=["H1", "H2", "H3"],
            datetime=[
                f"{a.isoformat()}/{b.isoformat()}"
                for a, b in [
                    (start, start + pd.Timedelta(hours=3)),
                    (start + pd.Timedelta(hours=1), start + pd.Timedelta(hours=2)),
                    (start, start + pd.Timedelta(days=1)),
                ]
            ],
            survey_complete=[True, True, True],
            weather_stop=[False, False, True],
        )
    )
    count = pd.DataFrame(
        dict(
            count_id=["O1", "O2"],
            survey_id=["H1", "H2"],
            datetime=[None, None],
            count=[3, pd.NA],
            count_category=["normal"] * 2,
        )
    )
    result = daily_coverage(count, survey).set_index("date")
    first = result.loc["2020-09-01"]
    assert first.survey_hours == 3 and first.surveys == 2
    assert first.entries == 2 and first["count"] == 3 and pd.isna(first.count_reverse)
    assert first.complete == 2 and first.weather_stop == 1 and first.incomplete == 0
    second = result.loc["2020-09-02"]
    assert second.survey_hours == 0 and second.surveys == 0 and second.weather_stop == 1
    assert second.entries == 0 and pd.isna(second["count"])


def test_daily_coverage_uses_local_dates_dst_hours_and_unlinked_final_records():
    survey = pd.DataFrame(
        dict(
            survey_id=["S1"],
            survey_complete=[False],
            weather_stop=[False],
            datetime=["2020-10-24T22:00:00Z/2020-10-25T23:00:00Z"],
        )
    )
    count = pd.DataFrame(
        dict(
            count_id=["C1", "C2", "C3", "C3-reverse"],
            survey_id=["S1", None, None, None],
            datetime=[None, "2020-10-26", "2020-10-27", "2020-10-27"],
            count=[0, pd.NA, 2, 1],
            count_category=["normal", "normal", "normal", "reverse"],
        )
    )
    result = daily_coverage(count, survey).set_index("date")
    assert pd.isna(result.loc["2020-10-25", "survey_hours"])
    assert result.loc["2020-10-25", "incomplete"] == 1
    assert result.loc["2020-10-25", "count"] == 0
    assert pd.isna(result.loc["2020-10-26", "count"])
    assert result.loc["2020-10-26", "entries"] == 1 and result.loc["2020-10-26", "surveys"] == 0
    assert pd.isna(result.loc["2020-10-26", "survey_hours"])
    assert result.loc["2020-10-27", "count_reverse"] == 1


def test_report_filters_use_complete_candidates_and_download_follows_table():
    from defile_dataset.report import render

    rows = pd.DataFrame({"duration_hours": [12.5, 15.5] * 110})
    check = Check(
        "Long surveys",
        "warn",
        "",
        rows,
        key="long-surveys",
        group="Surveys",
        filter_column="duration_hours",
        filter_threshold=16,
        file="validation_findings.csv",
    )
    document = render([check], {})
    assert document.count("<tr data-filter-value=") == 220
    assert 'data-filter-value="12.5"' in document and 'data-sort="15.5"' in document
    assert "finding-threshold" in document and 'value="16"' in document
    assert "Suivis longs" in document and "report-language" in document
    assert document.index("</table>") < document.index('href="validation_findings.csv"')
    assert 'aria-sort="none"' in document


def test_compact_survey_times_keep_next_day_marker_and_full_sort_value():
    from defile_dataset.report import render

    rows = pd.DataFrame(
        {
            "date": pd.to_datetime(["2025-08-24"]),
            "start": pd.to_datetime(["2025-08-24T04:00:00Z"]),
            "end": pd.to_datetime(["2025-08-25T04:00:00Z"]),
            "night_minutes": [500.0],
        }
    )
    check = Check(
        "Surveys into the night",
        "warn",
        "",
        rows,
        key="surveys-into-the-night",
        filter_column="night_minutes",
    )
    document = render([check], {})
    assert "08-25 06:00" in document
    assert 'data-sort="2025-08-25 04:00:00+00:00"' in document


def test_duration_filter_allows_short_periods():
    from defile_dataset.report import render

    check = Check(
        "Empty surveys",
        "warn",
        "",
        pd.DataFrame({"duration_hours": [0.25, 2.0]}),
        key="survey-status-empty-example",
        filter_column="duration_hours",
    )
    document = render([check], {})
    assert 'min="0"' in document and 'data-filter-value="0.25"' in document


def test_entry_offset_filter_uses_minutes_and_default_tolerance():
    from defile_dataset.report import render

    check = Check(
        "Entry times outside their source period",
        "warn",
        "",
        pd.DataFrame({"outside_minutes": [5, 6]}),
        key="entry-times-outside-their-source-period",
        filter_column="outside_minutes",
        filter_threshold=5,
    )
    document = render([check], {})
    assert "Outside period by more than (min)" in document and 'value="5"' in document
    assert 'data-filter-value="5"' in document and 'data-filter-value="6"' in document


def test_coverage_report_shows_final_daily_figure_and_no_old_coverage_tables():
    from defile_dataset.report import render

    coverage = pd.DataFrame(
        dict(
            date=pd.to_datetime(["2020-09-01"]),
            year=[2020],
            day_of_year=[245],
            entries=[1],
            surveys=[1],
            survey_hours=[3],
            count=[pd.NA],
            count_reverse=[0],
            count_local=[pd.NA],
        )
    )
    document = render(
        [], {}, coverage=coverage, coverage_season=dict(start_day_of_year=196, end_day_of_year=335)
    )
    assert "coverage-metric" in document and "coverage/plotly.min.js" in document
    assert "Plotly.react" in document and "coverage-chart" in document
    assert '"start_day_of_year": 196, "end_day_of_year": 335' in document
    assert "daily_coverage.csv" in document and "coverage-download" in document
    assert "Precision and missing attributes" not in document
    assert "released_surveys" not in document and "source_surveys" not in document
    assert "yearly_coverage.csv" not in document
    assert '"count": null' in document and '"count_reverse": 0' in document
