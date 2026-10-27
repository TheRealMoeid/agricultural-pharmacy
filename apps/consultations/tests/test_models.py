"""Tests for ConsultationRequest.

Look-alike characters (Arabic and Persian kaf and yeh) are written as escapes,
as in the other test files.
"""
import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import transaction

from apps.catalog.models import Crop
from apps.consultations.models import MESSAGE_MAX_LENGTH, ConsultationRequest

pytestmark = pytest.mark.django_db

Kind = ConsultationRequest.Kind
Status = ConsultationRequest.Status
NotificationStatus = ConsultationRequest.NotificationStatus

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
PHONE = "09112747628"
REQUIRED = "این فیلد را پر کنید."


def data(**overrides):
    base = {"kind": Kind.QUESTION, "name": "\u0639\u0644\u06cc", "phone": PHONE, "message": "\u0633\u0644\u0627\u0645"}
    return {**base, **overrides}


def visit(**overrides):
    base = {"kind": Kind.FARM_VISIT, "message": "", "village_or_address": "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"}
    return data(**{**base, **overrides})


def make(**overrides):
    return ConsultationRequest.objects.create(**data(**overrides))


# --- defaults and identity ----------------------------------------------------------


def test_a_new_request_starts_as_new_with_no_notification_attempted():
    request = make()
    request.refresh_from_db()
    assert request.status == Status.NEW
    assert request.notification_status == NotificationStatus.NOT_ATTEMPTED
    assert request.notification_detail == ""
    assert request.created_at is not None
    assert request.crop is None


def test_the_stored_values_are_the_ones_other_code_relies_on():
    # The admin sorts on "-status" (new above handled); phase 3 will write these strings.
    assert Status.values == ["new", "handled"]
    assert sorted(Status.values, reverse=True)[0] == "new"
    assert Kind.values == ["question", "farm_visit"]
    assert NotificationStatus.values == ["not_attempted", "sent", "failed"]


def test_str_names_the_kind_and_the_person_but_never_the_phone_number():
    text = str(make(phone="+98 911 274 7628"))
    assert "\u0639\u0644\u06cc" in text
    assert Kind.QUESTION.label in text
    assert "911" not in text
    assert "0911" not in text


def test_newest_request_comes_first():
    first = make(name="a")
    second = make(name="b")
    assert list(ConsultationRequest.objects.all()) == [second, first]


# --- required fields per kind ---------------------------------------------------------


def test_a_question_needs_its_text():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(message="  \n ")).full_clean()
    assert list(exc.value.message_dict) == ["message"]


def test_a_question_does_not_need_an_address():
    ConsultationRequest(**data(village_or_address="")).full_clean()


def test_a_farm_visit_needs_an_address():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**visit(village_or_address="  ")).full_clean()
    assert list(exc.value.message_dict) == ["village_or_address"]


def test_a_farm_visit_does_not_need_a_message():
    ConsultationRequest(**visit(message="")).full_clean()


def test_a_kind_that_does_not_exist_is_refused():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(kind="other")).full_clean()
    assert "kind" in exc.value.message_dict


def test_a_status_that_does_not_exist_is_refused():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(status="done")).full_clean()
    assert "status" in exc.value.message_dict


# --- name ---------------------------------------------------------------------------------


def test_an_empty_name_is_refused_once_by_the_field():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(name="")).full_clean()
    assert len(exc.value.message_dict["name"]) == 1


def test_a_name_of_only_spaces_is_refused_once_with_our_message():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(name=" \u200c  ")).full_clean()
    assert exc.value.message_dict["name"] == [REQUIRED]


def test_a_name_that_grows_when_cleaned_is_refused_instead_of_crashing():
    # Six U+FDFA fit in 100 characters as typed (6); cleaned they are 108.
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(name="\ufdfa" * 6)).full_clean()
    assert "name" in exc.value.message_dict


def test_an_address_that_grows_when_cleaned_is_refused():
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**visit(village_or_address="\ufdfa" * 15)).full_clean()  # 270 > 255
    assert "village_or_address" in exc.value.message_dict


def test_name_and_address_are_cleaned_when_saved():
    request = make(name="  " + ARABIC_KAF + "\u0631\u06cc\u0645   \u062e\u0627\u0646 ", village_or_address="  \u0631\u0648\u0633\u062a\u0627   " + ARABIC_KAF)
    request.refresh_from_db()
    assert request.name == PERSIAN_KAF + "\u0631\u06cc\u0645 \u062e\u0627\u0646"
    assert request.village_or_address == "\u0631\u0648\u0633\u062a\u0627 " + PERSIAN_KAF


# --- phone ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "typed",
    ["09112747628", "+98 911 274 7628", "0911-274-7628", "(+98)09112747628", "\u06f0\u06f9\u06f1\u06f1\u06f2\u06f7\u06f4\u06f7\u06f6\u06f2\u06f8"],
)
def test_the_phone_is_stored_in_one_canonical_form(typed):
    request = ConsultationRequest(**data(phone=typed))
    request.full_clean()
    request.save()
    request.refresh_from_db()
    assert request.phone == PHONE


@pytest.mark.parametrize("bad", ["12345", "02112345678", "abc", "  "])
def test_an_invalid_phone_is_refused(bad):
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(phone=bad)).full_clean()
    assert "phone" in exc.value.message_dict


# --- message --------------------------------------------------------------------------------


def test_the_message_keeps_its_line_breaks_but_unifies_letters_and_trims():
    request = make(message="\n  " + ARABIC_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645  \n")
    request.refresh_from_db()
    assert request.message == PERSIAN_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645"


def test_a_message_of_exactly_the_limit_is_fine_and_one_more_is_not():
    ConsultationRequest(**data(message="x" * MESSAGE_MAX_LENGTH)).full_clean()
    with pytest.raises(ValidationError) as exc:
        ConsultationRequest(**data(message="x" * (MESSAGE_MAX_LENGTH + 1))).full_clean()
    assert "message" in exc.value.message_dict


# --- crop -------------------------------------------------------------------------------------


def test_the_crop_is_optional_and_can_be_set():
    crop = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    request = make(crop=crop)
    assert list(crop.consultation_requests.all()) == [request]


def test_deleting_a_crop_keeps_the_request():
    crop = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    request = make(crop=crop)
    crop.delete()
    request.refresh_from_db()
    assert request.crop is None


# --- migrations ---------------------------------------------------------------------------------


def test_migrations_are_in_sync_with_the_models():
    call_command("makemigrations", "consultations", "--check", "--dry-run")
