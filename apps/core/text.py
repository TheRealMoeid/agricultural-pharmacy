"""Persian text normalization.

People type Persian in many slightly different ways: Arabic keyboards produce
the Arabic forms of yeh and kaf, digits come as Persian, Arabic-Indic or plain
ASCII, "half spaces" (ZWNJ) are used inconsistently, and text pasted from
messengers carries invisible direction marks. Without cleaning, a search for
"قارچ‌کش" would miss a product stored as "قارچکش".

Three levels, from gentle to aggressive:

- normalize_letters(): unifies the letters themselves. Safe for anything.
- normalize_text(): also cleans whitespace and invisible characters. Keeps
  ZWNJ and digits as typed, so the result is still fine to show or store.
- normalize_for_search(): builds a comparison key. Not meant for display.

What is deliberately NOT done: folding أ/إ into ا, or ة into ه. Those can
change the meaning of a word, and they are rare in everyday Persian.
"""
import re
import unicodedata

ZWNJ = "\u200c"

# Arabic letters that Persian writes differently.
_LETTER_MAP = str.maketrans(
    {
        "\u064a": "\u06cc",  # ARABIC LETTER YEH       -> ARABIC LETTER FARSI YEH
        "\u0649": "\u06cc",  # ARABIC LETTER ALEF MAKSURA -> ARABIC LETTER FARSI YEH
        "\u0643": "\u06a9",  # ARABIC LETTER KAF       -> ARABIC LETTER KEHEH
    }
)

# Persian (U+06F0..) and Arabic-Indic (U+0660..) digits to ASCII.
_DIGIT_MAP = {}
for _i in range(10):
    _DIGIT_MAP[0x06F0 + _i] = str(_i)
    _DIGIT_MAP[0x0660 + _i] = str(_i)

# Tatweel (kashida) and the Arabic vowel marks (harakat).
_DECORATION_RE = re.compile("[\u0640\u064b-\u065f\u0670]")

# Characters with no visible effect that only get in the way: zero-width
# space, zero-width joiner, left-to-right and right-to-left marks, the bidi
# embedding controls, and the byte order mark. ZWNJ is NOT in this list.
_INVISIBLE_RE = re.compile("[\u200b\u200d\u200e\u200f\u202a-\u202e\u2066-\u2069\ufeff]")

# A run made of whitespace and ZWNJ that contains at least one real
# whitespace character. A ZWNJ next to a space means nothing.
_SPACE_RUN_RE = re.compile(r"[\s\u200c]*\s[\s\u200c]*")
_ZWNJ_RUN_RE = re.compile("\u200c{2,}")


def normalize_digits(text: str | None) -> str:
    """Turn Persian and Arabic-Indic digits into ASCII digits."""
    if not text:
        return ""
    return text.translate(_DIGIT_MAP)


def normalize_letters(text: str | None) -> str:
    """Unify the letters, and remove kashida and vowel marks.

    Arabic yeh, alef maksura and kaf become the Persian yeh and kaf. Compatibility
    forms (Arabic presentation forms, full-width characters) are folded by
    Unicode NFKC. Whitespace is left alone, so this is also safe for
    multi-line text such as a customer's message.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_LETTER_MAP)
    return _DECORATION_RE.sub("", text)


def normalize_text(text: str | None) -> str:
    """Clean a single-line piece of text for storing or comparing.

    Does everything normalize_letters() does, then drops invisible junk,
    collapses every run of whitespace (including non-breaking spaces and
    newlines) into one space, and trims the ends. ZWNJ and digits stay as typed.
    Because newlines are collapsed, use normalize_letters() for multi-line text.
    """
    text = normalize_letters(text)
    if not text:
        return ""
    text = _INVISIBLE_RE.sub("", text)
    text = _SPACE_RUN_RE.sub(" ", text)
    text = _ZWNJ_RUN_RE.sub(ZWNJ, text)
    return text.strip(" " + ZWNJ)


def normalize_for_search(text: str | None) -> str:
    """Build the key that search compares on, for both stored and typed text.

    On top of normalize_text(): digits become ASCII, ZWNJ is removed (so
    "قارچ‌کش" and "قارچکش" give the same key), and Latin letters are
    case-folded (so "Mancozeb" matches "mancozeb").

    A normal space is NOT removed, so "قارچ کش" gives a different key from
    "قارچکش". The search code is expected to split the query into words and
    check each word on its own.
    """
    text = normalize_digits(normalize_text(text))
    return text.replace(ZWNJ, "").casefold()
