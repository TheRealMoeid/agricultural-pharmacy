"""Tests for the files in static/: the built CSS and the fonts (D36, D37). No database needed."""
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest
from django.contrib.staticfiles import finders

ROOT = Path(__file__).resolve().parents[3]
FONTS = ["Vazirmatn-Regular.woff2", "Vazirmatn-Bold.woff2"]

# Letters and signs that show up in Persian text typed by people, including the
# Arabic yeh and kaf, the Persian-only letters, both kinds of digit, and the
# half space.
NEEDED = "ءآأإؤئابپتثجچحخدذرزژسشصضطظعغفقکگلمنوهیيك" + "۰۱۲۳۴۵۶۷۸۹0123456789" + "،؛؟«»‌ .-/:%()" + "abcXYZ"


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def css_text():
    return (ROOT / "static" / "css" / "site.css").read_text(encoding="utf-8")


def test_the_built_stylesheet_and_fonts_can_be_found_by_django():
    for path in ["css/site.css", "css/input.css", "fonts/OFL.txt", *[f"fonts/{f}" for f in FONTS]]:
        assert finders.find(path), path


def test_the_built_css_was_made_by_the_pinned_tailwind_version():
    tailwind = load_script("tailwind")
    first_line = css_text().splitlines()[0]
    assert first_line.startswith(f"/*! tailwindcss v{tailwind.VERSION} ")


def test_the_built_css_is_up_to_date(tmp_path):
    tailwind = load_script("tailwind")
    if not tailwind.binary_path().exists():
        pytest.skip("Tailwind is not installed here: python scripts/tailwind.py install")
    fresh = tmp_path / "fresh.css"
    assert tailwind.run("--output", str(fresh), "--minify") == 0
    assert fresh.read_text(encoding="utf-8") == css_text(), (
        "static/css/site.css is out of date: run python scripts/tailwind.py build and commit it"
    )


def test_every_file_the_css_points_to_exists_and_none_is_on_another_site():
    urls = re.findall(r"url\(([^)]*)\)", css_text())
    assert urls
    for url in urls:
        url = url.strip("\"'")
        assert not re.match(r"(https?:)?//", url), url
        target = (ROOT / "static" / "css" / url).resolve()
        assert target.is_file(), url


def test_both_font_weights_are_declared_with_font_display_swap():
    css = css_text()
    assert css.count("@font-face") == 2
    assert css.count("font-display:swap") == 2
    assert "font-weight:400" in css and "font-weight:700" in css


def test_only_the_templates_are_scanned_for_classes():
    # Tailwind's automatic scan of the whole project is off (source(none) in
    # input.css). With it on, the word "container" in the docs and tests pulled
    # in a ".container" rule that no template uses. (A word inside a template,
    # even in a comment, can still add a rule; that is normal and tiny.)
    assert ".container" not in css_text()


def test_the_stylesheet_is_small():
    # An estimate with room to grow: 10 KB when written.
    assert (ROOT / "static" / "css" / "site.css").stat().st_size < 20_000


@pytest.mark.parametrize("name", FONTS)
def test_each_font_file_is_a_small_woff2(name):
    path = ROOT / "static" / "fonts" / name
    assert path.read_bytes()[:4] == b"wOF2"
    assert path.stat().st_size < 30_000  # about 22 KB when cut down; the full font is about 50 KB


@pytest.mark.parametrize("name", FONTS)
def test_the_cut_down_fonts_still_have_every_letter_people_type(name):
    ttlib = pytest.importorskip("fontTools.ttLib")
    cmap = ttlib.TTFont(ROOT / "static" / "fonts" / name).getBestCmap()
    missing = [ch for ch in NEEDED if ord(ch) not in cmap]
    assert not missing, missing


def test_the_fonts_cover_the_stores_own_default_text():
    ttlib = pytest.importorskip("fontTools.ttLib")
    from apps.core.models import SiteSettings

    text = "".join(str(SiteSettings._meta.get_field(f).default) for f in ("store_name", "address", "working_hours"))
    cmap = ttlib.TTFont(ROOT / "static" / "fonts" / FONTS[0]).getBestCmap()
    assert [ch for ch in text if ord(ch) not in cmap] == []


def test_the_font_license_stays_next_to_the_font_files():
    text = (ROOT / "static" / "fonts" / "OFL.txt").read_text(encoding="utf-8")
    assert "SIL Open Font License" in text


def test_the_font_script_makes_the_two_files_the_site_uses():
    assert [f"Vazirmatn-{w}.woff2" for w in load_script("subset_fonts").WEIGHTS] == FONTS


def test_the_font_script_asks_for_every_letter_people_type():
    unicodes = load_script("subset_fonts").UNICODES
    wanted = set()
    for part in unicodes.split(","):
        low, _, high = part.removeprefix("U+").partition("-")
        wanted.update(range(int(low, 16), int(high or low, 16) + 1))
    assert [ch for ch in NEEDED if ord(ch) not in wanted] == []
