"""Run the Tailwind CSS standalone command-line tool, at one pinned version.

The standalone build needs no Node.js or npm (D36). It is one file that is
downloaded once into `.tools/` (not in Git), checked against the checksum
published with the release, and then run.

    python scripts/tailwind.py install   download the pinned version (once, about 110 MB)
    python scripts/tailwind.py build     static/css/input.css -> static/css/site.css, minified
    python scripts/tailwind.py watch     rebuild on every change while you work on templates

The built `static/css/site.css` is committed, so the server and the Docker
image never need this tool. Rebuild and commit it whenever a template or
`input.css` changes how the site looks. A test fails if the committed file is
out of date (it needs the tool installed to check).

To move to a newer Tailwind: change VERSION and CHECKSUMS below (the checksums
come from the `sha256sums.txt` file on the release page), run `install`, then
`build`, and commit the new `site.css`.
"""
import hashlib
import os
import platform
import stat
import subprocess
import sys
import urllib.request
from pathlib import Path

VERSION = "4.3.3"

# From https://github.com/tailwindlabs/tailwindcss/releases/download/v4.3.3/sha256sums.txt
CHECKSUMS = {
    "linux-x64": "dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a",
    "linux-arm64": "55fd0b241214eff3de1e8ee4f22796662f2d2e7a49bcfca7477cfd0bac398195",
    "macos-x64": "7922e0953f2110c05976e3bf58f14e643d90427575e766b7d433f5f80cbee7e1",
    "macos-arm64": "cdf646702987a743464dff4d9c60fd4480d1c1e73dd819a9a67f1078815dce9d",
    "windows-x64": "e0e260ce048014e9268f6237ff18f8ccf02cef521cbd0ae04e82c2cdf7aa3955",
}

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / ".tools"
INPUT = ROOT / "static" / "css" / "input.css"
OUTPUT = ROOT / "static" / "css" / "site.css"
URL = "https://github.com/tailwindlabs/tailwindcss/releases/download/v{version}/tailwindcss-{key}{ext}"


def platform_key() -> str:
    """The name of this machine's build, as used in CHECKSUMS."""
    machine = platform.machine().lower()
    arm = machine in ("arm64", "aarch64")
    intel = machine in ("x86_64", "amd64")
    if sys.platform.startswith("win") and intel:
        return "windows-x64"
    if sys.platform == "darwin" and (arm or intel):
        return "macos-arm64" if arm else "macos-x64"
    if sys.platform.startswith("linux") and (arm or intel):
        return "linux-arm64" if arm else "linux-x64"
    raise SystemExit(f"No Tailwind standalone build for {sys.platform} / {machine}.")


def _extension(key: str) -> str:
    return ".exe" if key.startswith("windows") else ""


def binary_path() -> Path:
    key = platform_key()
    return TOOLS_DIR / f"tailwindcss-{VERSION}-{key}{_extension(key)}"


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify(path: Path, key: str) -> None:
    """Raise SystemExit unless the file is the release's file for `key`."""
    actual = sha256_of(path)
    if actual != CHECKSUMS[key]:
        raise SystemExit(
            f"Checksum mismatch for {path.name}: expected {CHECKSUMS[key]}, got {actual}. "
            "The download is not the expected file."
        )


def install() -> Path:
    key = platform_key()
    target = binary_path()
    if target.exists():
        verify(target, key)
        print(f"Already installed: {target}")
        return target
    TOOLS_DIR.mkdir(exist_ok=True)
    url = URL.format(version=VERSION, key=key, ext=_extension(key))
    partial = target.with_name(target.name + ".part")
    print(f"Downloading {url}")
    try:
        urllib.request.urlretrieve(url, partial)
        verify(partial, key)
    except BaseException:
        partial.unlink(missing_ok=True)
        raise
    os.replace(partial, target)
    target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"Installed {target}")
    return target


def run(*extra: str) -> int:
    binary = binary_path()
    if not binary.exists():
        raise SystemExit("Tailwind is not installed yet. Run: python scripts/tailwind.py install")
    return subprocess.call([str(binary), "--input", str(INPUT), *extra], cwd=ROOT)


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ""
    if command == "install":
        install()
        return 0
    if command == "build":
        output = argv[2] if len(argv) >= 3 and argv[1] == "--output" else str(OUTPUT)
        return run("--output", output, "--minify")
    if command == "watch":
        return run("--output", str(OUTPUT), "--watch")
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
