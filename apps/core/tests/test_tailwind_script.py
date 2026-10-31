"""Tests for scripts/tailwind.py. No network and no database needed."""
import hashlib
import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def tw(monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location("tailwind_under_test", ROOT / "scripts" / "tailwind.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "TOOLS_DIR", tmp_path / ".tools")
    return module


def pretend(monkeypatch, platform_name, machine):
    monkeypatch.setattr(sys, "platform", platform_name)
    monkeypatch.setattr("platform.machine", lambda: machine)


# --- which build is this machine -----------------------------------------------------------------


@pytest.mark.parametrize(
    "platform_name, machine, key",
    [
        ("win32", "AMD64", "windows-x64"),
        ("darwin", "arm64", "macos-arm64"),
        ("darwin", "x86_64", "macos-x64"),
        ("linux", "x86_64", "linux-x64"),
        ("linux", "aarch64", "linux-arm64"),
    ],
)
def test_every_common_machine_maps_to_one_build(tw, monkeypatch, platform_name, machine, key):
    pretend(monkeypatch, platform_name, machine)
    assert tw.platform_key() == key


@pytest.mark.parametrize("platform_name, machine", [("win32", "ARM64"), ("freebsd13", "x86_64"), ("linux", "riscv64")])
def test_an_unsupported_machine_says_so(tw, monkeypatch, platform_name, machine):
    pretend(monkeypatch, platform_name, machine)
    with pytest.raises(SystemExit) as exc:
        tw.platform_key()
    assert "No Tailwind standalone build" in str(exc.value)


def test_there_is_a_checksum_for_every_build_we_can_pick(tw):
    assert set(tw.CHECKSUMS) == {"windows-x64", "macos-arm64", "macos-x64", "linux-x64", "linux-arm64"}
    assert all(re.fullmatch(r"[0-9a-f]{64}", value) for value in tw.CHECKSUMS.values())
    assert len(set(tw.CHECKSUMS.values())) == 5


def test_only_the_windows_file_ends_in_exe_and_the_version_is_in_the_name(tw, monkeypatch):
    pretend(monkeypatch, "win32", "AMD64")
    assert tw.binary_path().name == f"tailwindcss-{tw.VERSION}-windows-x64.exe"
    pretend(monkeypatch, "linux", "x86_64")
    assert tw.binary_path().name == f"tailwindcss-{tw.VERSION}-linux-x64"


def test_the_checksum_for_this_machine_matches_the_installed_program_if_there_is_one():
    spec = importlib.util.spec_from_file_location("tailwind_real", ROOT / "scripts" / "tailwind.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    installed = module.binary_path()
    if not installed.exists():
        pytest.skip("Tailwind is not installed here: python scripts/tailwind.py install")
    module.verify(installed, module.platform_key())


def test_the_download_address_is_the_official_release(tw):
    url = tw.URL.format(version=tw.VERSION, key="linux-x64", ext="")
    assert url == f"https://github.com/tailwindlabs/tailwindcss/releases/download/v{tw.VERSION}/tailwindcss-linux-x64"


# --- checking and installing -----------------------------------------------------------------------


def test_verify_accepts_the_right_file_and_refuses_any_other(tw, monkeypatch, tmp_path):
    good = tmp_path / "good"
    good.write_bytes(b"the real thing")
    monkeypatch.setitem(tw.CHECKSUMS, "linux-x64", hashlib.sha256(b"the real thing").hexdigest())
    tw.verify(good, "linux-x64")
    bad = tmp_path / "bad"
    bad.write_bytes(b"something else")
    with pytest.raises(SystemExit) as exc:
        tw.verify(bad, "linux-x64")
    assert "Checksum mismatch" in str(exc.value)


def fake_download(content):
    def retrieve(url, filename):
        Path(filename).write_bytes(content)

    return retrieve


def test_install_stores_a_verified_download_and_makes_it_runnable(tw, monkeypatch):
    pretend(monkeypatch, "linux", "x86_64")
    monkeypatch.setitem(tw.CHECKSUMS, "linux-x64", hashlib.sha256(b"binary").hexdigest())
    monkeypatch.setattr("urllib.request.urlretrieve", fake_download(b"binary"))
    path = tw.install()
    assert path == tw.binary_path()
    assert path.read_bytes() == b"binary"
    if os.name != "nt":  # Windows has no executable bit; sys.platform is faked above, so it cannot be used here
        assert path.stat().st_mode & 0o111
    assert [p.name for p in tw.TOOLS_DIR.iterdir()] == [path.name]  # no leftover partial file


def test_install_keeps_nothing_if_the_download_is_not_the_expected_file(tw, monkeypatch):
    pretend(monkeypatch, "linux", "x86_64")
    monkeypatch.setattr("urllib.request.urlretrieve", fake_download(b"tampered"))
    with pytest.raises(SystemExit):
        tw.install()
    assert list(tw.TOOLS_DIR.iterdir()) == []


def test_install_keeps_nothing_if_the_download_fails_halfway(tw, monkeypatch):
    pretend(monkeypatch, "linux", "x86_64")

    def broken(url, filename):
        Path(filename).write_bytes(b"half")
        raise OSError("connection lost")

    monkeypatch.setattr("urllib.request.urlretrieve", broken)
    with pytest.raises(OSError):
        tw.install()
    assert list(tw.TOOLS_DIR.iterdir()) == []


def test_install_does_not_download_again_and_notices_a_damaged_file(tw, monkeypatch):
    pretend(monkeypatch, "linux", "x86_64")
    monkeypatch.setitem(tw.CHECKSUMS, "linux-x64", hashlib.sha256(b"binary").hexdigest())
    monkeypatch.setattr("urllib.request.urlretrieve", fake_download(b"binary"))
    path = tw.install()
    monkeypatch.setattr("urllib.request.urlretrieve", lambda *a: pytest.fail("downloaded again"))
    assert tw.install() == path
    path.write_bytes(b"damaged")
    with pytest.raises(SystemExit):
        tw.install()


def test_running_before_installing_says_what_to_do(tw, monkeypatch):
    pretend(monkeypatch, "linux", "x86_64")
    with pytest.raises(SystemExit) as exc:
        tw.run("--minify")
    assert "python scripts/tailwind.py install" in str(exc.value)


def test_an_unknown_command_prints_the_usage_and_fails(tw, capsys):
    assert tw.main(["frobnicate"]) == 2
    assert "python scripts/tailwind.py install" in capsys.readouterr().out
    assert tw.main([]) == 2


# --- the commands -----------------------------------------------------------------------------------


@pytest.fixture
def recorded(tw, monkeypatch):
    calls = []
    monkeypatch.setattr(tw, "run", lambda *args: calls.append(args) or 0)
    return calls


def test_build_makes_the_minified_site_stylesheet(tw, recorded):
    assert tw.main(["build"]) == 0
    assert recorded == [("--output", str(tw.OUTPUT), "--minify")]
    assert tw.OUTPUT == ROOT / "static" / "css" / "site.css"
    assert tw.INPUT == ROOT / "static" / "css" / "input.css"


def test_build_can_write_somewhere_else_and_is_still_minified(tw, recorded):
    tw.main(["build", "--output", "/tmp/x.css"])
    assert recorded == [("--output", "/tmp/x.css", "--minify")]


def test_watch_rebuilds_the_site_stylesheet_without_minifying(tw, recorded):
    tw.main(["watch"])
    assert recorded == [("--output", str(tw.OUTPUT), "--watch")]


def test_the_install_command_installs(tw, monkeypatch):
    called = []
    monkeypatch.setattr(tw, "install", lambda: called.append(True))
    assert tw.main(["install"]) == 0
    assert called == [True]
