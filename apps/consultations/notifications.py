"""Telling the store that a new request has arrived (D3, D42).

The request is stored first and is the source of truth: the staff inbox in the
admin always has it, whether or not a message goes out. This module turns a
request into a Persian message and hands it to the channel the store chose,
Telegram through the store's own bot, then reports what happened so the caller
can store it on the request. Nothing is raised at the customer: a send that
fails is our problem, never theirs.

Two configuration values turn the channel on, both from the environment (see
.env.example): TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID. With either one empty
nothing is sent and the request says so, which is what a development machine
without a bot should do; it is never an error.

Only post_to_telegram() talks to Telegram: it is the one place that knows the
API, the timeout and the error texts, so it is the one place tests replace.
The bot token is a secret. It is part of the API address, so no address, no
exception message and no log line here ever carries it; the detail stored on a
request is a short Persian sentence for staff.
"""
import json
import logging
from http.client import HTTPException
from typing import NamedTuple
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings

from apps.core.jalali import format_jalali_datetime
from apps.core.phone import format_display

from .models import ConsultationRequest

logger = logging.getLogger(__name__)

NotificationStatus = ConsultationRequest.NotificationStatus

# Telegram's Bot API. The token goes into the path, as the API requires.
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"

# A customer is waiting on the other side of a form submission, so the send
# gets a few seconds and no more. Telegram answers in well under one second
# when it is reachable at all.
TIMEOUT = 5

# How much of Telegram's own explanation is kept. Long enough to say "chat not
# found", short enough to stay a reason and not a log.
DETAIL_MAX_LENGTH = 200

TITLE = "🔔 درخواست تازه از سایت"

NOT_CONFIGURED = "تلگرام تنظیم نشده است؛ اطلاع‌رسانی خاموش است"
UNREACHABLE = "به تلگرام دسترسی نبود"
UNREADABLE = "پاسخ تلگرام خوانا نبود"
REJECTED = "تلگرام پیام را نپذیرفت"
# Used by the view when the notifier itself breaks, which should never happen.
CRASHED = "خطا در اطلاع‌رسانی"


class NotificationOutcome(NamedTuple):
    """What to store on the request: one of the three notification states, plus a reason."""

    status: str
    detail: str = ""


class NotificationError(Exception):
    """Why a message did not go out. Short, in Persian, and never the token."""


def is_configured() -> bool:
    """True when both values are set. Either one missing turns notifications off."""
    return bool(settings.TELEGRAM_BOT_TOKEN.strip()) and bool(settings.TELEGRAM_CHAT_ID.strip())


def format_message(consultation) -> str:
    """The Persian message the store receives.

    A question carries its text and no address, a farm visit its address and
    an optional text, so the lines below cover both without asking which kind
    this is: what is filled in is shown. The time is the same Jalali stamp the
    admin inbox shows, so the two places agree.
    """
    lines = [
        TITLE,
        "",
        f"نوع: {consultation.get_kind_display()}",
        f"نام: {consultation.name}",
        f"تلفن: {format_display(consultation.phone)}",
    ]
    if consultation.crop_id:
        lines.append(f"گیاه: {consultation.crop.name}")
    if consultation.village_or_address:
        lines.append(f"روستا یا نشانی: {consultation.village_or_address}")
    if consultation.message:
        # The text can be several lines, so the label gets a line of its own.
        lines += ["متن پیام:", consultation.message]
    lines.append(f"زمان: {format_jalali_datetime(consultation.created_at)}")
    return "\n".join(lines)


def post_to_telegram(text: str) -> None:
    """Send one message to the store's chat. Raises NotificationError on any failure.

    One plain HTTPS POST to the Bot API, with the standard library: a bot token
    and a chat id need no library, and the project adds no dependency it does
    not need. Timeouts, refused connections, wrong addresses (Telegram answers
    400, 401, 403 or 429), answers that are not JSON, and a 200 that still says
    "not ok" all end up as the same short reason, because the customer's form
    submission has to carry on either way.
    """
    request = Request(
        TELEGRAM_API.format(token=settings.TELEGRAM_BOT_TOKEN),
        data=urlencode({"chat_id": settings.TELEGRAM_CHAT_ID, "text": text}).encode(),
        method="POST",
    )
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            status = response.getcode()
            body = response.read()
    except HTTPError as exc:  # Telegram's own answer to a bad token, chat or text
        raise NotificationError(f"تلگرام پاسخ {exc.code} داد") from None
    except (OSError, HTTPException):  # no network, no DNS, timeout, broken answer
        raise NotificationError(UNREACHABLE) from None

    if status != 200:
        raise NotificationError(f"تلگرام پاسخ {status} داد")
    try:
        answer = json.loads(body or b"{}")
    except ValueError:
        raise NotificationError(UNREADABLE) from None
    if not isinstance(answer, dict) or not answer.get("ok"):
        # Telegram answers 200 with {"ok": false, "description": "..."} for
        # some refusals, for example a chat the bot was removed from.
        description = answer.get("description", "").strip() if isinstance(answer, dict) else ""
        raise NotificationError(_clip(f"{REJECTED}: {description}" if description else REJECTED))


def send_consultation_notification(consultation) -> NotificationOutcome:
    """Try to tell the store about this request, and report what happened.

    Never raises for anything Telegram does; the caller stores the answer on
    the request. (A bug in here would still not reach the customer: the view
    keeps its own guard around this call.)
    """
    if not is_configured():
        logger.warning(
            "Telegram is not configured (token or chat id empty); request %s was stored without a notification",
            consultation.pk,
        )
        return NotificationOutcome(NotificationStatus.NOT_ATTEMPTED, NOT_CONFIGURED)

    try:
        post_to_telegram(format_message(consultation))
    except NotificationError as exc:
        logger.warning("The Telegram notification for request %s failed: %s", consultation.pk, exc)
        return NotificationOutcome(NotificationStatus.FAILED, str(exc))

    logger.info("The Telegram notification for request %s was sent", consultation.pk)
    return NotificationOutcome(NotificationStatus.SENT, "")


def _clip(text: str) -> str:
    """Telegram's explanation, kept to a reason."""
    return text if len(text) <= DETAIL_MAX_LENGTH else text[: DETAIL_MAX_LENGTH - 1] + "…"
