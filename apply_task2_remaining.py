"""Applies the three small, context-sensitive edits for phase 3, task 2
(the Telegram notification adapter, D42) directly, without going through
`git apply`'s hunk-context matching, which has failed twice for these three
files for reasons that could not be pinned down from uploaded copies alone.

Run from the repository root:

    python apply_task2_remaining.py

Each edit is an exact substring search-and-replace. If a search text is not
found, the script stops immediately, prints the file and roughly where it
expected the match, and changes nothing in that file -- so a partial failure
never leaves a file half-edited. Run it once; it is not meant to be run
twice on a file it has already changed (the second run will correctly fail,
since the "old" text will already be gone).
"""
import sys
from pathlib import Path

EDITS = {
    "apps/core/jalali.py": [
        (
            "import datetime\n",
            "import datetime\n\nfrom django.utils import timezone\n",
        ),
        (
            "def gregorian_to_jalali(date: datetime.date) -> tuple[int, int, int]:\n"
            '    """A Gregorian `datetime.date` to a (jalali_year, jalali_month, jalali_day) tuple."""\n'
            "    return _d2j(_g2d(date.year, date.month, date.day))\n",
            "def gregorian_to_jalali(date: datetime.date) -> tuple[int, int, int]:\n"
            '    """A Gregorian `datetime.date` to a (jalali_year, jalali_month, jalali_day) tuple."""\n'
            "    return _d2j(_g2d(date.year, date.month, date.day))\n"
            "\n"
            "\n"
            'def format_jalali_datetime(value) -> str:\n'
            '    """A stored datetime as "1405/01/01 15:30": Jalali date, store-local time.\n'
            "\n"
            "    The stamp the admin inbox shows and the Telegram notification carries, so\n"
            "    the two never disagree. ASCII digits, as everywhere staff-facing.\n"
            '    """\n'
            "    local = timezone.localtime(value)\n"
            "    jy, jm, jd = gregorian_to_jalali(local.date())\n"
            '    return f"{jy:04d}/{jm:02d}/{jd:02d} {local:%H:%M}"\n',
        ),
    ],
    "config/settings/base.py": [
        (
            'ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")\n',
            'ADMIN_URL = env("DJANGO_ADMIN_URL", default="admin/")\n'
            "\n"
            "# The store's own Telegram bot, which tells the staff about a new consultation\n"
            "# request (D3, D42). Both values come from the environment; with either one\n"
            "# empty nothing is sent and the request says so, which is what a development\n"
            "# machine without a bot needs. The token is a secret: never in Git, a log line\n"
            "# or a traceback (it is part of the Bot API address, so the address is never\n"
            "# logged either).\n"
            'TELEGRAM_BOT_TOKEN = env("DJANGO_TELEGRAM_BOT_TOKEN", default="")\n'
            'TELEGRAM_CHAT_ID = env("DJANGO_TELEGRAM_CHAT_ID", default="")\n',
        ),
    ],
    "apps/consultations/admin.py": [
        (
            "from django.contrib import admin, messages\n"
            "from django.db.models import Q\n"
            "from django.utils import timezone\n"
            "from django.utils.html import format_html\n"
            "\n"
            "from apps.core.jalali import gregorian_to_jalali\n"
            "from apps.core.phone import format_display, to_international\n"
            "from apps.core.text import normalize_digits, normalize_letters, normalize_text\n"
            "\n"
            "from .models import ConsultationRequest\n"
            "\n"
            "Status = ConsultationRequest.Status\n"
            "\n"
            "\n"
            "def format_jalali_datetime(value) -> str:\n"
            '    """A stored datetime as "1405/01/01 15:30": Jalali date, store-local time."""\n'
            "    local = timezone.localtime(value)\n"
            "    jy, jm, jd = gregorian_to_jalali(local.date())\n"
            '    return f"{jy:04d}/{jm:02d}/{jd:02d} {local:%H:%M}"\n',
            "from django.contrib import admin, messages\n"
            "from django.db.models import Q\n"
            "from django.utils.html import format_html\n"
            "\n"
            "from apps.core.jalali import format_jalali_datetime\n"
            "from apps.core.phone import format_display, to_international\n"
            "from apps.core.text import normalize_digits, normalize_letters, normalize_text\n"
            "\n"
            "from .models import ConsultationRequest\n"
            "\n"
            "Status = ConsultationRequest.Status\n",
        ),
    ],
}


def main() -> int:
    root = Path(__file__).resolve().parent
    failures = []
    for rel_path, edits in EDITS.items():
        path = root / rel_path
        if not path.exists():
            print(f"SKIP  {rel_path}: file not found at {path}")
            failures.append(rel_path)
            continue
        text = path.read_text(encoding="utf-8")
        new_text = text
        ok = True
        for old, new in edits:
            # Checked first and on its own: "old" can be a literal prefix of
            # "new" (e.g. an added import line), so after a first successful
            # run "old" would still be found inside the now-edited text and a
            # second run would double the edit instead of failing cleanly.
            if new in new_text:
                print(f"SKIP  {rel_path}: this edit is already present (file already edited).")
                ok = None  # neither a failure nor a fresh success; don't write, don't complain
                break
            if old not in new_text:
                print(f"FAIL  {rel_path}: expected text not found.")
                print(f"      First 300 characters of the file as found:")
                print("      " + repr(text[:300]))
                ok = False
                break
            new_text = new_text.replace(old, new, 1)
        if ok is True:
            path.write_text(new_text, encoding="utf-8")
            print(f"OK    {rel_path}: edit applied.")
        elif ok is False:
            failures.append(rel_path)
        # ok is None: already done, nothing to write, not a failure.

    if failures:
        print(f"\n{len(failures)} file(s) could not be edited: {', '.join(failures)}")
        print("Nothing was changed in those files. Paste the FAIL output above back to Claude.")
        return 1
    print("\nAll three files edited successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
