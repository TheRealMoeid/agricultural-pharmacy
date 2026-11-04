"""Tests for the public consultation form.

As in the other tests, look-alike characters (Arabic and Persian kaf) are
written as escapes.
"""
import pytest

from apps.catalog.models import Crop
from apps.consultations.forms import ConsultationForm
from apps.consultations.models import MESSAGE_MAX_LENGTH, ConsultationRequest

pytestmark = pytest.mark.django_db

Kind = ConsultationRequest.Kind
ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
NAME = "\u0639\u0644\u06cc \u0631\u0636\u0627\u06cc\u06cc"  # علی رضایی
ASK = "\u0628\u0631\u06af\u0647\u0627\u06cc \u06af\u0646\u062f\u0645 \u0632\u0631\u062f \u0634\u062f\u0647"  # برگهای گندم زرد شده
VILLAGE = "\u0622\u0642\u200c\u0622\u0628\u0627\u062f"  # آق‌آباد


def question(**overrides):
    return {"name": NAME, "phone": "09121234567", "message": ASK, **overrides}


def visit(**overrides):
    return {"name": NAME, "phone": "09121234567", "village_or_address": VILLAGE, **overrides}


def form(kind, data):
    return ConsultationForm(data, kind=kind)


# --- which fields each form has ------------------------------------------------------------------


def test_the_question_form_has_no_address_field():
    assert list(form(Kind.QUESTION, {}).fields) == ["name", "phone", "crop", "message", "website"]


def test_the_farm_visit_form_has_the_address_field():
    assert "village_or_address" in form(Kind.FARM_VISIT, {}).fields


def test_required_fields_per_kind():
    q = form(Kind.QUESTION, {}).fields
    assert [n for n in ("name", "phone", "crop", "message") if q[n].required] == ["name", "phone", "message"]
    v = form(Kind.FARM_VISIT, {}).fields
    assert [n for n in ("name", "phone", "crop", "message", "village_or_address") if v[n].required] == [
        "name", "phone", "village_or_address"
    ]


def test_the_crop_choices_are_the_catalogs_crops():
    wheat = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    assert list(form(Kind.QUESTION, {}).fields["crop"].queryset) == [wheat]


# --- saving --------------------------------------------------------------------------------------


def test_a_valid_question_is_saved_with_its_kind_and_a_canonical_phone():
    f = form(Kind.QUESTION, question(phone="+98 912 123 4567"))
    assert f.is_valid(), f.errors
    saved = f.save()
    saved.refresh_from_db()
    assert saved.kind == Kind.QUESTION
    assert saved.phone == "09121234567"
    assert saved.status == ConsultationRequest.Status.NEW
    assert saved.notification_status == ConsultationRequest.NotificationStatus.NOT_ATTEMPTED


def test_a_valid_farm_visit_is_saved_without_a_message():
    f = form(Kind.FARM_VISIT, visit())
    assert f.is_valid(), f.errors
    saved = f.save()
    assert (saved.kind, saved.message, saved.village_or_address) == (Kind.FARM_VISIT, "", VILLAGE)


def test_the_optional_crop_is_saved_when_chosen():
    wheat = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    f = form(Kind.QUESTION, question(crop=wheat.pk))
    assert f.is_valid(), f.errors
    assert f.save().crop == wheat


def test_the_honeypot_is_never_saved_anywhere():
    f = form(Kind.QUESTION, question(website=""))
    assert f.is_valid()
    assert "website" not in f.save().__dict__


def test_the_text_is_cleaned_like_everywhere_else():
    f = form(Kind.QUESTION, question(name="  " + ARABIC_KAF + "\u0631\u06cc\u0645   \u062e\u0627\u0646 "))
    assert f.is_valid(), f.errors
    assert f.save().name == PERSIAN_KAF + "\u0631\u06cc\u0645 \u062e\u0627\u0646"


# --- refusals ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("missing", ["name", "phone", "message"])
def test_a_question_needs_name_phone_and_message(missing):
    f = form(Kind.QUESTION, question(**{missing: ""}))
    assert not f.is_valid()
    assert list(f.errors) == [missing]


@pytest.mark.parametrize("missing", ["name", "phone", "village_or_address"])
def test_a_farm_visit_needs_name_phone_and_address(missing):
    f = form(Kind.FARM_VISIT, visit(**{missing: ""}))
    assert not f.is_valid()
    assert list(f.errors) == [missing]


@pytest.mark.parametrize("bad", ["12345", "02112345678", "abc", "0912123456"])
def test_an_invalid_phone_is_refused_with_the_persian_message(bad):
    f = form(Kind.QUESTION, question(phone=bad))
    assert not f.is_valid()
    assert "\u0634\u0645\u0627\u0631\u0647 \u0645\u0648\u0628\u0627\u06cc\u0644 \u0645\u0639\u062a\u0628\u0631 \u0646\u06cc\u0633\u062a" in f.errors["phone"][0]


def test_a_message_of_only_spaces_is_refused_for_a_question():
    f = form(Kind.QUESTION, question(message="  \n "))
    assert not f.is_valid()
    assert "message" in f.errors


def test_a_message_over_the_limit_is_refused():
    assert form(Kind.QUESTION, question(message="x" * MESSAGE_MAX_LENGTH)).is_valid()
    assert not form(Kind.QUESTION, question(message="x" * (MESSAGE_MAX_LENGTH + 1))).is_valid()


def test_a_crop_that_does_not_exist_is_refused():
    f = form(Kind.QUESTION, question(crop=99999))
    assert not f.is_valid()
    assert "crop" in f.errors


def test_the_kind_comes_from_the_view_not_from_the_posted_data():
    f = form(Kind.QUESTION, question(kind=Kind.FARM_VISIT))
    assert f.is_valid()
    assert f.save().kind == Kind.QUESTION


def test_the_phone_field_is_a_tel_input_without_a_duplicate_type():
    html = str(form(Kind.QUESTION, {})["phone"])
    assert html.count("type=") == 1 and 'type="tel"' in html
    assert 'dir="ltr"' in html and 'inputmode="numeric"' in html
