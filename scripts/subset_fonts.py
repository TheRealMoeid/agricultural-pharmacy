"""Cut the Vazirmatn font down to the characters this site uses (D37).

The full font is about 50 KB per weight; the site only needs Persian letters
(including the Arabic yeh and kaf people still type), digits, punctuation and
basic Latin. Cut down, each weight is about 22 KB, which matters on the weak
mobile connections many visitors have.

This is a one-time step. The result is committed in `static/fonts/`, so
nobody needs to run it again unless the character set or the font version
changes.

    pip install fonttools brotli
    npm pack vazirmatn@33.0.3       (or download the package any other way)
    tar xzf vazirmatn-33.0.3.tgz
    python scripts/subset_fonts.py package/fonts/webfonts

Source: the `vazirmatn` package, version 33.0.3, SIL Open Font License
(`static/fonts/OFL.txt` has to stay next to the font files).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "static" / "fonts"
WEIGHTS = ["Regular", "Bold"]

# Basic Latin, no-break space, guillemets, Arabic comma/semicolon/question mark,
# the Arabic letters (U+0621-063A, U+0641-064A), kashida and vowel marks, the
# four Persian-only letters (پ چ ژ گ) plus ک and ی, Persian digits, percent and
# separators, ZWNJ and the direction marks, dashes, quotes, ellipsis and minus.
UNICODES = (
    "U+0020-007E,U+00A0,U+00AB,U+00BB,"
    "U+060C,U+061B,U+061F,U+0621-063A,U+0640-0652,U+0654,U+066A-066C,U+0670,"
    "U+067E,U+0686,U+0698,U+06A9,U+06AF,U+06CC,U+06F0-06F9,"
    "U+200C-200F,U+2010-2015,U+2018-201D,U+2026,U+2212"
)


def main(source: str) -> None:
    from fontTools import subset

    source_dir = Path(source)
    OUT.mkdir(parents=True, exist_ok=True)
    for weight in WEIGHTS:
        source_file = source_dir / f"Vazirmatn-{weight}.woff2"
        target = OUT / f"Vazirmatn-{weight}.woff2"
        subset.main(
            [
                str(source_file),
                f"--unicodes={UNICODES}",
                "--layout-features=*",  # keep the joining and mark-placement rules
                "--flavor=woff2",
                "--no-hinting",
                f"--output-file={target}",
            ]
        )
        print(f"{target.name}: {target.stat().st_size} bytes")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(sys.argv[1])
