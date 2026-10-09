"""Clocks in prose need a quantity and event scope, not just a clock-shaped substring."""

import pandas as pd

from defile_dataset.source_text import (
    clock_timestamp,
    point_from_text,
    split_timed_counts,
    timed_age_components,
    timed_events,
    timed_groups,
)


def test_point_clock_removes_only_converted_text():
    for clock in ["16h29", "11h31", "16h10"]:
        assert point_from_text("à " + clock, 1) == (clock, "")
    assert point_from_text("à 13h55.", 2) == ("13h55", "")
    assert point_from_text("2 à 13h55", 2) == ("13h55", "")
    assert point_from_text("16h13 avec 11 milans noirs", 1) == ("16h13", "avec 11 milans noirs")
    assert point_from_text("à 10h30 - NB : un autre groupe passe à 10h16", 111) == (
        "10h30",
        "NB : un autre groupe passe à 10h16",
    )
    assert point_from_text("2 adultes, 3 jeunes à 9h47", 5) == ("9h47", "2 adultes, 3 jeunes")


def test_ranges_approximate_times_durations_and_partial_counts_are_not_whole_count_points():
    for text in [
        "vers 9h30",
        "de 11h15 à 11h45",
        "Flux de 9h30 à 11h",
        "JPM seul jusqu’à 12h30",
        "Après 2h30 de suivi",
        "2h30 de suivi",
        "13h15-13h25",
        "13h55 environ",
        "13h55?",
        "2 à 13h55",
        "1:16h20;2:16h36",
        "3 à 12h35 - 17 à 12h50",
    ]:
        assert point_from_text(text, 3) is None
    assert timed_groups("40:15h06;6:15h55.", 46) == [(40, "15h06"), (6, "15h55")]
    assert timed_groups("78 à 14h05 - 35 à 14h10 - 93 à 14h45 - 28 à 14h57", 234) == [
        (78, "14h05"),
        (35, "14h10"),
        (93, "14h45"),
        (28, "14h57"),
    ]
    assert timed_groups("1:10h15-1:10h20", 3) is None
    assert timed_groups("de 11h15 à 11h45", 9) is None


def test_local_clock_uses_seasonal_utc_offset_and_leaves_dst_ambiguity_unresolved():
    assert clock_timestamp("2015-09-15", "8h56") == pd.Timestamp("2015-09-15T06:56:00Z")
    assert clock_timestamp("2015-11-15", "08:56:12") == pd.Timestamp("2015-11-15T07:56:12Z")
    assert pd.isna(clock_timestamp("2015-10-25", "02:30"))


def test_supplied_timed_group_examples_keep_clocks_and_explicit_ages():
    examples = [
        ("2 ad à 13h43   et\u00a0 1 jeune à 13h58", 3, [(2, "13h43", "A"), (1, "13h58", "1")]),
        ("1 adulte à 15h18, 1 adulte à 15h30", 2, [(1, "15h18", "A"), (1, "15h30", "A")]),
        (
            "37 (36   adultes et 1 jeune) à 13h25 - 4 (cc avec 2 jeunes) à 13h53",
            41,
            [(36, "13h25", "A"), (1, "13h25", "1"), (2, "13h53", "1"), (2, "13h53", None)],
        ),
        ("1 (1ac)   à 13h10 et 8 à 13h20", 9, [(1, "13h10", "1"), (8, "13h20", None)]),
        ("1 ad à   14h15 - 1 jeune à 14h44", 2, [(1, "14h15", "A"), (1, "14h44", "1")]),
        ("4 à 12h35 - 17 à 12h50", 21, [(4, "12h35", None), (17, "12h50", None)]),
        (
            "4 à   12h16 - 13 à 12h31 - 43 à   12h56.",
            60,
            [(4, "12h16", None), (13, "12h31", None), (43, "12h56", None)],
        ),
    ]
    for text, count, expected in examples:
        events = timed_events(text, count)
        actual = [
            (n, event["clock"], age)
            for event in events
            for n, age, _ in timed_age_components(event["count"], event["description"])
        ]
        assert actual == expected
    assert timed_age_components(4, "cc avec 2 jeunes")[-1] == (2, None, "cc")


def test_timed_age_groups_are_projected_without_guessing_the_unaged_remainder():
    source = pd.DataFrame(
        [
            dict(
                observation_id="H1",
                source_count_id="H1",
                source="historical",
                date=pd.Timestamp("2015-09-15"),
                datetime=pd.NaT,
                count=41,
                comment="37 (36 adultes et 1 jeune) à 13h25 - 4 (cc avec 2 jeunes) à 13h53",
                remark=None,
                age=None,
                sex=None,
                plumage=None,
            )
        ]
    )
    original = source.copy(deep=True)
    result = split_timed_counts(source)
    assert result["count"].tolist() == [36, 1, 2, 2]
    assert result.age.fillna("").tolist() == ["A", "1", "1", ""]
    assert (
        result.datetime.tolist()
        == [pd.Timestamp("2015-09-15T11:25Z")] * 2 + [pd.Timestamp("2015-09-15T11:53Z")] * 2
    )
    assert result.comment_residual.fillna("").tolist() == ["", "", "", "cc"]
    assert result.observation_id.is_unique
    pd.testing.assert_frame_equal(source, original)


def test_recorded_age_totals_resolve_only_a_unique_timed_remainder():
    source = pd.DataFrame(
        [
            dict(
                observation_id="H1-part1",
                source_count_id="H1",
                source="historical",
                date=pd.Timestamp("2015-09-15"),
                datetime=pd.NaT,
                count=38,
                comment="37 (36 adultes et 1 jeune) à 13h25 - 4 (cc avec 2 jeunes) à 13h53",
                remark=None,
                age="A",
                sex=None,
                plumage=None,
            ),
            dict(
                observation_id="H1-part2",
                source_count_id="H1",
                source="historical",
                date=pd.Timestamp("2015-09-15"),
                datetime=pd.NaT,
                count=3,
                comment="37 (36 adultes et 1 jeune) à 13h25 - 4 (cc avec 2 jeunes) à 13h53",
                remark=None,
                age="1",
                sex=None,
                plumage=None,
            ),
        ]
    )
    result = split_timed_counts(source)
    assert result["count"].tolist() == [36, 1, 2, 2]
    assert result.age.tolist() == ["A", "1", "1", "A"]
    assert result.groupby("age")["count"].sum().to_dict() == {"1": 3, "A": 38}
    source["comment"] = "4 à 12h16 - 13 à 12h31 - 24 à 12h56"
    interval = split_timed_counts(source)
    assert interval["count"].tolist() == [38, 3] and interval.age.tolist() == ["A", "1"]
    assert interval.datetime_interval.eq("2015-09-15T10:16:00Z/2015-09-15T10:56:00Z").all()
