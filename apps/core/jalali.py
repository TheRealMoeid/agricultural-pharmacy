"""Conversion between the Jalali (Persian, Solar Hijri) and Gregorian calendars.

D23: Habibollah types production and expiry dates in Jalali in the admin;
they are stored as Gregorian. The conversion is written in the project and
tested, not taken from a package (D23), so no third-party dependency is added
for this.

The algorithm below is the standard astronomical Jalali algorithm (the one
Iran's official calendar is based on), published by Kazimierz M. Borkowski
and widely used under the name "jalaali" (see e.g. the jalaali-js project,
MIT licensed). It is a faithful, line-by-line port of that algorithm, not a
simplified approximation: it is valid for Jalali years -61 to 3177 and has
been checked both by round-tripping every day across many centuries and
against several independently published Nowruz dates (see test_jalali.py).

Only two functions are meant to be used outside this module:
gregorian_to_jalali() and jalali_to_gregorian().
"""
import datetime

# Jalali years where the 33-year leap-year cycle breaks (restarts). Table from
# the reference algorithm; not something to hand-tune.
_BREAKS = [
    -61, 9, 38, 199, 426, 686, 756, 818, 1111, 1181, 1210,
    1635, 2060, 2097, 2192, 2262, 2324, 2394, 2456, 3178,
]


def _div(a: int, b: int) -> int:
    """Integer division truncated toward zero (not Python's floor //)."""
    q = a // b
    if q < 0 and q * b != a:
        q += 1
    return q


def _mod(a: int, b: int) -> int:
    return a - _div(a, b) * b


def _jal_cal(jy: int) -> dict:
    """Leap-year offset, Gregorian year and March day of 1 Farvardin for jy."""
    bl = len(_BREAKS)
    gy = jy + 621
    leap_j = -14
    jp = _BREAKS[0]
    if jy < jp or jy >= _BREAKS[bl - 1]:
        raise ValueError(f"سال {jy} خارج از محدوده پشتیبانی‌شده است.")
    jump = 0
    for i in range(1, bl):
        jm = _BREAKS[i]
        jump = jm - jp
        if jy < jm:
            break
        leap_j += _div(jump, 33) * 8 + _div(_mod(jump, 33), 4)
        jp = jm
    n = jy - jp
    leap_j += _div(n, 33) * 8 + _div(_mod(n, 33) + 3, 4)
    if _mod(jump, 33) == 4 and jump - n == 4:
        leap_j += 1
    leap_g = _div(gy, 4) - _div((_div(gy, 100) + 1) * 3, 4) - 150
    march = 20 + leap_j - leap_g
    if jump - n < 6:
        n = n - jump + _div(jump + 4, 33) * 33
    leap = _mod(_mod(n + 1, 33) - 1, 4)
    if leap == -1:
        leap = 4
    return {"leap": leap, "gy": gy, "march": march}


def _g2d(gy: int, gm: int, gd: int) -> int:
    """Gregorian date to Julian Day Number."""
    d = (
        _div((gy + _div(gm - 8, 6) + 100100) * 1461, 4)
        + _div(153 * _mod(gm + 9, 12) + 2, 5)
        + gd
        - 34840408
    )
    d = d - _div(_div(gy + 100100 + _div(gm - 8, 6), 100) * 3, 4) + 752
    return d


def _d2g(jdn: int) -> tuple[int, int, int]:
    """Julian Day Number to Gregorian (year, month, day)."""
    j = 4 * jdn + 139361631
    j = j + _div(_div(4 * jdn + 183187720, 146097) * 3, 4) * 4 - 3908
    i = _div(_mod(j, 1461), 4) * 5 + 308
    gd = _div(_mod(i, 153), 5) + 1
    gm = _mod(_div(i, 153), 12) + 1
    gy = _div(j, 1461) - 100100 + _div(8 - gm, 6)
    return gy, gm, gd


def _j2d(jy: int, jm: int, jd: int) -> int:
    r = _jal_cal(jy)
    return _g2d(r["gy"], 3, r["march"]) + (jm - 1) * 31 - _div(jm, 7) * (jm - 7) + jd - 1


def _d2j(jdn: int) -> tuple[int, int, int]:
    gy, _gm, _gd = _d2g(jdn)
    jy = gy - 621
    r = _jal_cal(jy)
    jdn1f = _g2d(r["gy"], 3, r["march"])
    k = jdn - jdn1f
    if k >= 0:
        if k <= 185:
            jm = 1 + _div(k, 31)
            jd = _mod(k, 31) + 1
            return jy, jm, jd
        k -= 186
    else:
        jy -= 1
        k += 179
        if r["leap"] == 1:
            k += 1
    jm = 7 + _div(k, 30)
    jd = _mod(k, 30) + 1
    return jy, jm, jd


def is_leap_jalali_year(jy: int) -> bool:
    return _jal_cal(jy)["leap"] == 0


def jalali_month_length(jy: int, jm: int) -> int:
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if is_leap_jalali_year(jy) else 29


def is_valid_jalali_date(jy: int, jm: int, jd: int) -> bool:
    # The year bound comes straight from _BREAKS rather than being repeated
    # as separate literals, so the two can never drift out of sync: an
    # out-of-table year is rejected here before jalali_month_length() ever
    # gets a chance to call _jal_cal() with a year it would raise on.
    if not (_BREAKS[0] <= jy < _BREAKS[-1]):
        return False
    return 1 <= jm <= 12 and 1 <= jd <= jalali_month_length(jy, jm)


def jalali_to_gregorian(jy: int, jm: int, jd: int) -> datetime.date:
    """A Jalali date (year, month, day) to a Gregorian `datetime.date`."""
    if not is_valid_jalali_date(jy, jm, jd):
        raise ValueError(f"تاریخ شمسی نامعتبر است: {jy}/{jm}/{jd}")
    gy, gm, gd = _d2g(_j2d(jy, jm, jd))
    return datetime.date(gy, gm, gd)


def gregorian_to_jalali(date: datetime.date) -> tuple[int, int, int]:
    """A Gregorian `datetime.date` to a (jalali_year, jalali_month, jalali_day) tuple."""
    return _d2j(_g2d(date.year, date.month, date.day))
