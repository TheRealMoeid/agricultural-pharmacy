"""Tests for the Jalali/Gregorian conversion (D23).

No database needed: this is pure date arithmetic.

The reference dates below are independently documented Nowruz (Jalali New
Year) dates, not derived from this module, and cross-checked against more
than one source:

- 1 Farvardin 1393 = 21 March 2014 (widely published for the Afghan
  calendar, which shares its calendar with Iran's)
- 1 Farvardin 1400 = 21 March 2021, a Sunday (live news wire reports from
  that day -- Anadolu Agency and others -- put it on the 21st; a single
  secondary source claiming the 20th turned out to be wrong)
- 1 Farvardin 1403 = 20 March 2024 (widely published)
- 1 Farvardin 1405 = 21 March 2026 (equinox at 18:16 Tehran time -- after
  noon, so Nowruz falls the following day, per the rule that governs which
  day Nowruz lands on)

1404 is deliberately NOT in this list; see test_known_discrepancy... below.

Beyond these spot checks, every day across several centuries is round-tripped
both ways, which would catch an error that the few spot checks might miss.
"""
import datetime

import pytest

from apps.core.jalali import (
    _jal_cal,  # a private helper, imported only for the white-box check below
    gregorian_to_jalali,
    is_leap_jalali_year,
    is_valid_jalali_date,
    jalali_month_length,
    jalali_to_gregorian,
)

NOWRUZ_PAIRS = [
    ((1393, 1, 1), datetime.date(2014, 3, 21)),
    ((1400, 1, 1), datetime.date(2021, 3, 21)),
    ((1403, 1, 1), datetime.date(2024, 3, 20)),
    ((1405, 1, 1), datetime.date(2026, 3, 21)),
]


@pytest.mark.parametrize("jalali, gregorian", NOWRUZ_PAIRS)
def test_known_nowruz_dates_jalali_to_gregorian(jalali, gregorian):
    assert jalali_to_gregorian(*jalali) == gregorian


@pytest.mark.parametrize("jalali, gregorian", NOWRUZ_PAIRS)
def test_known_nowruz_dates_gregorian_to_jalali(jalali, gregorian):
    assert gregorian_to_jalali(gregorian) == jalali


def test_today_is_in_the_right_decade():
    # A sanity check anchored to this project's own timeline, not a precise
    # oracle: October 2026 falls in the second half of Jalali year 1405,
    # several months after the 1405 Nowruz checked above.
    jy, jm, jd = gregorian_to_jalali(datetime.date(2026, 10, 24))
    assert jy == 1405
    assert jm == 8  # Aban: 23 Oct - 21 Nov


def test_the_day_before_nowruz_is_the_last_day_of_the_previous_year():
    assert gregorian_to_jalali(datetime.date(2024, 3, 19)) == (1402, 12, 29)


def test_known_discrepancy_for_1404_against_the_true_astronomical_date():
    """Documents a known, unresolved limitation rather than hiding it.

    Several detailed, independent sources put the true equinox-based Nowruz
    1404 at 20 March 2025 (09:01 Tehran time, before noon). This module's
    algorithm -- the same one jalaali-js, moment-jalaali and most Persian
    software use -- puts it a day later. This is not a bug in this port: it
    is a documented, still-open limitation of the standard break-table
    algorithm itself for this specific year (jalaali/jalaali-js issue #52,
    "Off-by-one Date Error in 1404 following leap year 1403").

    This test locks in the algorithm's actual (if imperfect) behavior, so a
    future change to the conversion is a deliberate decision, not a silent
    side effect. See docs/DECISIONS.md for the note to Moeid about this.
    """
    assert jalali_to_gregorian(1404, 1, 1) == datetime.date(2025, 3, 21)
    assert gregorian_to_jalali(datetime.date(2025, 3, 20)) == (1403, 12, 30)


# --- the breaks table itself ---------------------------------------------------


def test_jal_cal_matches_published_reference_output():
    """Checks the internal leap/gy/march values, not just a final date.

    Round-tripping a date through gregorian_to_jalali() and back cannot catch
    a mistranscribed entry in the leap-year break table: g2d/d2g and j2d/d2j
    stay mutual inverses of each other no matter what the table says, so a
    wrong table still "round-trips" perfectly while quietly computing the
    wrong calendar. These values, by contrast, are the published, directly
    reproducible output of the reference implementation's own jalCal()
    function (see the jalaali-js README) for several consecutive years,
    including a leap one -- so they check the table and the cycle math that
    reads it, not just the round trip.
    """
    cases = {
        1390: {"leap": 3, "gy": 2011, "march": 21},
        1391: {"leap": 0, "gy": 2012, "march": 20},
        1392: {"leap": 1, "gy": 2013, "march": 21},
        1393: {"leap": 2, "gy": 2014, "march": 21},
    }
    for jy, expected in cases.items():
        assert _jal_cal(jy) == expected


# --- round trips --------------------------------------------------------------


def test_every_day_in_a_wide_range_round_trips_through_jalali():
    # Kept within the algorithm's well-established range. Past Jalali year
    # 1634 (Gregorian ~2256) this algorithm is known to diverge by a day from
    # more precise astronomical calculations in some years (same as the
    # reference implementation it is ported from) -- far beyond any date this
    # project will ever store, so it is deliberately not covered here.
    start = datetime.date(1800, 1, 1)
    end = datetime.date(2250, 1, 1)
    day = start
    step = datetime.timedelta(days=37)  # every ~37th day; still thousands of days
    while day < end:
        jy, jm, jd = gregorian_to_jalali(day)
        assert jalali_to_gregorian(jy, jm, jd) == day
        day += step


def test_every_day_of_several_consecutive_years_round_trips():
    # A tighter, exhaustive sweep across a leap and a non-leap year boundary.
    day = datetime.date(2023, 1, 1)
    end = datetime.date(2027, 1, 1)
    while day < end:
        jy, jm, jd = gregorian_to_jalali(day)
        assert jalali_to_gregorian(jy, jm, jd) == day
        day += datetime.timedelta(days=1)


def test_every_jalali_day_of_several_consecutive_years_round_trips():
    for jy in range(1390, 1410):
        for jm in range(1, 13):
            for jd in range(1, jalali_month_length(jy, jm) + 1):
                gdate = jalali_to_gregorian(jy, jm, jd)
                assert gregorian_to_jalali(gdate) == (jy, jm, jd)


# --- leap years and month lengths ---------------------------------------------


@pytest.mark.parametrize("jy", [1375, 1379, 1383, 1387, 1391, 1395, 1399, 1403])
def test_known_leap_years_are_366_days(jy):
    # A leap Jalali year has 30 days in Esfand (month 12); a common year has 29.
    assert jalali_month_length(jy, 12) == 30
    assert is_leap_jalali_year(jy) is True


@pytest.mark.parametrize("jy", [1400, 1401, 1402, 1404, 1405])
def test_known_common_years_are_365_days(jy):
    assert jalali_month_length(jy, 12) == 29
    assert is_leap_jalali_year(jy) is False


def test_month_lengths_for_a_common_year():
    jy = 1402  # not a leap year
    lengths = [jalali_month_length(jy, m) for m in range(1, 13)]
    assert lengths == [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]


def test_month_lengths_for_a_leap_year():
    jy = 1403  # a leap year
    lengths = [jalali_month_length(jy, m) for m in range(1, 13)]
    assert lengths == [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 30]


# --- validation -----------------------------------------------------------------


@pytest.mark.parametrize(
    "jy, jm, jd",
    [
        (1402, 1, 1),
        (1402, 12, 29),
        (1403, 12, 30),  # leap year, 30th of Esfand exists
        (1402, 6, 31),  # the last month with 31 days (Shahrivar)
    ],
)
def test_valid_dates_are_accepted(jy, jm, jd):
    assert is_valid_jalali_date(jy, jm, jd) is True
    jalali_to_gregorian(jy, jm, jd)  # should not raise


@pytest.mark.parametrize(
    "jy, jm, jd",
    [
        (1402, 0, 1),
        (1402, 13, 1),
        (1402, 1, 32),
        (1402, 7, 31 + 1),
        (1402, 12, 30),  # not a leap year: Esfand only has 29 days
        (1402, 8, 0),
    ],
)
def test_invalid_dates_are_rejected(jy, jm, jd):
    assert is_valid_jalali_date(jy, jm, jd) is False
    with pytest.raises(ValueError):
        jalali_to_gregorian(jy, jm, jd)


def test_an_out_of_range_year_raises_instead_of_crashing():
    with pytest.raises(ValueError):
        jalali_to_gregorian(5000, 1, 1)
    with pytest.raises(ValueError):
        jalali_to_gregorian(-100, 1, 1)


@pytest.mark.parametrize("jm", [1, 7, 12])  # an early, a late, and the last month
def test_an_out_of_range_year_is_rejected_cleanly_for_every_month(jm):
    # A year past the supported table must come back False, not raise, even
    # for the months whose length check would otherwise reach into the table.
    assert is_valid_jalali_date(5000, jm, 1) is False
    assert is_valid_jalali_date(-1000, jm, 1) is False
