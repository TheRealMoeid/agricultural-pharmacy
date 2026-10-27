"""Tests for Expert and FaqItem.

Look-alike characters (Arabic and Persian yeh and kaf, ZWNJ) are written as
escapes, as in the other test files. Do not "fix" them into literal letters.
"""
import io

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from PIL import Image, ImageFilter

from apps.pages.models import Expert, FaqItem

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

ARABIC_KAF = "\u0643"
PERSIAN_KAF = "\u06a9"
ARABIC_YEH = "\u064a"
PERSIAN_YEH = "\u06cc"
NAME = "\u0631\u062d\u0645\u062a\u200c\u0627\u0644\u0644\u0647"  # رحمت‌الله
DEGREE = "\u06a9\u0627\u0631\u0634\u0646\u0627\u0633\u06cc \u0632\u0631\u0627\u0639\u062a"  # کارشناسی زراعت


def make_expert(**overrides):
    return Expert.objects.create(**{"name": NAME, "degree": DEGREE, **overrides})


def upload(size=(1600, 1000), fmt="JPEG", name="IMG_2231.jpg"):
    return SimpleUploadedFile(name, make_image_bytes(fmt=fmt, size=size))


# --- Expert: fields ------------------------------------------------------------


def test_str_is_the_name():
    assert str(make_expert()) == NAME


def test_only_name_and_degree_are_required():
    expert = Expert(name=NAME, degree=DEGREE)
    expert.full_clean()
    expert.save()
    assert (expert.role, expert.experience, expert.specialty) == ("", "", "")
    assert not expert.photo


@pytest.mark.parametrize("missing", ["name", "degree"])
def test_a_required_field_cannot_be_blank(missing):
    data = {"name": NAME, "degree": DEGREE, missing: ""}
    with pytest.raises(ValidationError) as exc:
        Expert(**data).full_clean()
    assert list(exc.value.message_dict) == [missing]


@pytest.mark.parametrize("field", ["name", "degree"])
def test_a_required_field_with_only_spaces_is_refused_once_with_our_message(field):
    data = {"name": NAME, "degree": DEGREE, field: " \u200c  "}
    with pytest.raises(ValidationError) as exc:
        Expert(**data).full_clean()
    assert exc.value.message_dict[field] == ["این فیلد را پر کنید."]


def test_a_value_that_grows_when_cleaned_is_refused_instead_of_crashing():
    # U+FDFA is one character that NFKC turns into eighteen: seven of them fit in
    # the 120-character name as typed, but not once cleaned.
    with pytest.raises(ValidationError) as exc:
        Expert(name="\ufdfa" * 7, degree=DEGREE).full_clean()
    assert "name" in exc.value.message_dict


def test_text_is_cleaned_when_saved():
    expert = make_expert(
        name="  " + ARABIC_KAF + "\u0631\u06cc\u0645   " + "\u0645\u062d\u0645\u062f\u06cc ",
        role=ARABIC_YEH + "\u06a9 \u0633\u0645\u062a",
    )
    expert.refresh_from_db()
    assert expert.name == PERSIAN_KAF + "\u0631\u06cc\u0645 \u0645\u062d\u0645\u062f\u06cc"
    assert expert.role == PERSIAN_YEH + "\u06a9 \u0633\u0645\u062a"


def test_a_blank_optional_field_stays_blank():
    expert = make_expert(role="   ", experience="", specialty="  ")
    expert.refresh_from_db()
    assert (expert.role, expert.experience, expert.specialty) == ("", "", "")


def test_experts_are_ordered_by_order_then_creation():
    last = make_expert(name="c", order=2)
    first = make_expert(name="z", order=0)
    middle_a = make_expert(name="b", order=1)
    middle_b = make_expert(name="a", order=1)
    assert list(Expert.objects.all()) == [first, middle_a, middle_b, last]


# --- Expert: photo ---------------------------------------------------------------


def test_the_photo_settings_are_the_agreed_ones():
    field = Expert._meta.get_field("photo")
    assert field.max_side == 480
    assert field.quality == 80
    assert field.max_bytes == 30_000
    assert field.thumb_side is None


def test_the_field_does_not_freeze_its_validator_into_migrations():
    _name, _path, _args, kwargs = Expert._meta.get_field("photo").deconstruct()
    assert "validators" not in kwargs
    assert (kwargs["max_side"], kwargs["max_bytes"], kwargs["thumb_side"]) == (480, 30_000, None)


def test_a_photo_is_stored_as_one_small_webp_in_experts(media_root):
    expert = make_expert(photo=upload())
    expert.refresh_from_db()
    assert expert.photo.name.startswith("experts/")
    assert expert.photo.name.endswith(".webp")
    assert "IMG_2231" not in expert.photo.name
    stored = list((media_root / "experts").iterdir())
    assert len(stored) == 1  # no thumbnail
    with expert.photo.open("rb") as f:
        image = Image.open(io.BytesIO(f.read()))
    assert image.format == "WEBP"
    assert image.size == (480, 300)


def test_there_is_no_thumbnail_and_thumb_url_is_the_main_url():
    expert = make_expert(photo=upload())
    assert expert.photo.thumb_url == expert.photo.url


def test_a_busy_photo_is_held_to_the_size_budget(media_root):
    busy = Image.effect_noise((700, 700), 60).convert("RGB").filter(ImageFilter.GaussianBlur(1))
    buffer = io.BytesIO()
    busy.save(buffer, format="PNG")
    expert = make_expert(photo=SimpleUploadedFile("busy.png", buffer.getvalue()))
    assert (media_root / expert.photo.name).stat().st_size <= 30_000


def test_validation_refuses_a_non_image_with_a_message_on_the_photo_field():
    bad = SimpleUploadedFile("a.jpg", b"not an image")
    with pytest.raises(ValidationError) as exc:
        Expert(name=NAME, degree=DEGREE, photo=bad).full_clean()
    assert "تصویر معتبری نیست" in exc.value.message_dict["photo"][0]


def test_saving_again_does_not_process_the_photo_a_second_time():
    expert = make_expert(photo=upload())
    name = expert.photo.name
    expert.order = 3
    expert.save()
    expert.refresh_from_db()
    assert expert.photo.name == name


# --- FaqItem -----------------------------------------------------------------------


def make_faq(**overrides):
    return FaqItem.objects.create(**{"question": "q", "answer": "a", **overrides})


def test_faq_str_is_the_question():
    assert str(make_faq(question="\u0642\u06cc\u0645\u062a\u061f")) == "\u0642\u06cc\u0645\u062a\u061f"


@pytest.mark.parametrize("missing", ["question", "answer"])
def test_faq_question_and_answer_are_required(missing):
    with pytest.raises(ValidationError) as exc:
        FaqItem(**{"question": "q", "answer": "a", missing: ""}).full_clean()
    assert list(exc.value.message_dict) == [missing]


@pytest.mark.parametrize("field", ["question", "answer"])
def test_faq_text_with_only_spaces_is_refused_once_with_our_message(field):
    with pytest.raises(ValidationError) as exc:
        FaqItem(**{"question": "q", "answer": "a", field: " \n  "}).full_clean()
    assert exc.value.message_dict[field] == ["این فیلد را پر کنید."]


def test_faq_question_is_cleaned_like_a_single_line():
    item = make_faq(question="  " + ARABIC_KAF + "\u0627   \u0633\u0624\u0627\u0644 ")
    item.refresh_from_db()
    assert item.question == PERSIAN_KAF + "\u0627 \u0633\u0624\u0627\u0644"


def test_faq_answer_keeps_its_line_breaks_but_unifies_letters_and_trims():
    item = make_faq(answer="\n  " + ARABIC_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645  \n")
    item.refresh_from_db()
    assert item.answer == PERSIAN_KAF + "\u0627\u0631\n\n\u062f\u0648\u0645"


def test_faq_question_that_grows_when_cleaned_is_refused():
    with pytest.raises(ValidationError) as exc:
        FaqItem(question="\ufdfa" * 17, answer="a").full_clean()  # 17 * 18 = 306 > 300
    assert "question" in exc.value.message_dict


def test_faq_items_are_ordered_by_order_then_creation():
    late = make_faq(question="b", order=5)
    first = make_faq(question="z", order=0)
    second = make_faq(question="a", order=0)
    assert list(FaqItem.objects.all()) == [first, second, late]


# --- migrations -----------------------------------------------------------------------


def test_migrations_are_in_sync_with_the_models():
    call_command("makemigrations", "pages", "--check", "--dry-run")
