import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.pages.models import Expert, FaqItem

from .conftest import make_image_bytes

pytestmark = pytest.mark.django_db

KINDS = ["expert", "faqitem"]
NAME = "\u0631\u062d\u0645\u062a\u200c\u0627\u0644\u0644\u0647"
DEGREE = "\u06a9\u0627\u0631\u0634\u0646\u0627\u0633\u06cc \u0632\u0631\u0627\u0639\u062a"


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw-for-tests-123")
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def staff_client():
    """A staff member with no permissions at all."""
    user = get_user_model().objects.create_user("helper", password="pw-for-tests-123", is_staff=True)
    client = Client()
    client.force_login(user)
    return client


def url(kind, view, *args):
    return reverse(f"admin:pages_{kind}_{view}", args=args)


@pytest.mark.parametrize("kind", KINDS)
def test_changelist_opens(admin_client, kind):
    assert admin_client.get(url(kind, "changelist")).status_code == 200


@pytest.mark.parametrize("kind", KINDS)
def test_staff_without_permission_is_refused(staff_client, kind):
    assert staff_client.get(url(kind, "changelist")).status_code == 403
    assert staff_client.get(url(kind, "add")).status_code == 403


def test_adding_an_expert_with_everything_filled_in(admin_client):
    photo = SimpleUploadedFile("me.jpg", make_image_bytes(fmt="JPEG", size=(1200, 900)), content_type="image/jpeg")
    response = admin_client.post(
        url("expert", "add"),
        {
            "name": NAME,
            "degree": DEGREE,
            "role": "\u0645\u0633\u0626\u0648\u0644",
            "experience": "\u06f3\u06f0 \u0633\u0627\u0644",
            "specialty": "",
            "order": 1,
            "photo": photo,
        },
    )
    assert response.status_code == 302
    expert = Expert.objects.get()
    assert expert.experience == "\u06f3\u06f0 \u0633\u0627\u0644"
    assert expert.photo.name.startswith("experts/")


def test_adding_an_expert_with_degree_and_specialty_only(admin_client):
    # The shape of Habibollah's profile: no role, no experience, no photo yet.
    response = admin_client.post(
        url("expert", "add"),
        {"name": NAME, "degree": DEGREE, "role": "", "experience": "", "specialty": "\u06af\u06cc\u0627\u0647\u200c\u067e\u0632\u0634\u06a9\u06cc", "order": 2},
    )
    assert response.status_code == 302
    expert = Expert.objects.get()
    assert (expert.role, expert.experience) == ("", "")
    assert expert.specialty


def test_an_expert_without_a_name_is_not_saved(admin_client):
    response = admin_client.post(url("expert", "add"), {"name": "", "degree": DEGREE, "order": 0})
    assert response.status_code == 200
    assert Expert.objects.count() == 0


def test_a_non_image_is_refused_with_a_message_next_to_the_form(admin_client):
    bad = SimpleUploadedFile("notes.jpg", b"just some text", content_type="image/jpeg")
    response = admin_client.post(url("expert", "add"), {"name": NAME, "degree": DEGREE, "order": 0, "photo": bad})
    assert response.status_code == 200
    assert Expert.objects.count() == 0
    assert "errorlist" in response.content.decode()


def test_editing_an_expert_without_touching_the_photo_keeps_it(admin_client):
    photo = SimpleUploadedFile("me.jpg", make_image_bytes(), content_type="image/jpeg")
    admin_client.post(url("expert", "add"), {"name": NAME, "degree": DEGREE, "order": 0, "photo": photo})
    expert = Expert.objects.get()
    kept = expert.photo.name
    response = admin_client.post(url("expert", "change", expert.pk), {"name": NAME + " ۲", "degree": DEGREE, "order": 0})
    assert response.status_code == 302
    expert.refresh_from_db()
    assert expert.photo.name == kept


def test_the_edit_form_explains_that_empty_optional_lines_are_hidden(admin_client):
    expert = Expert.objects.create(name=NAME, degree=DEGREE)
    html = admin_client.get(url("expert", "change", expert.pk)).content.decode()
    assert html.count("اگر خالی بماند، نمایش داده نمی‌شود.") == 3


def test_adding_a_faq_item(admin_client):
    response = admin_client.post(url("faqitem", "add"), {"question": "\u0642\u06cc\u0645\u062a\u061f", "answer": "\u0628\u0627 \u0645\u0627 \u062a\u0645\u0627\u0633 \u0628\u06af\u06cc\u0631\u06cc\u062f.", "order": 0})
    assert response.status_code == 302
    assert FaqItem.objects.get().answer.startswith("\u0628\u0627")


def _reorder_post(first, second, first_order, second_order):
    return {
        "form-TOTAL_FORMS": "2",
        "form-INITIAL_FORMS": "2",
        "form-MIN_NUM_FORMS": "0",
        "form-MAX_NUM_FORMS": "1000",
        "form-0-id": first.pk,
        "form-0-order": str(first_order),
        "form-1-id": second.pk,
        "form-1-order": str(second_order),
        "_save": "Save",
    }


def test_experts_can_be_reordered_from_the_list(admin_client):
    a = Expert.objects.create(name="a", degree="d", order=1)
    b = Expert.objects.create(name="b", degree="d", order=2)
    response = admin_client.post(url("expert", "changelist"), _reorder_post(a, b, 5, 2))
    assert response.status_code == 302
    assert list(Expert.objects.all()) == [b, a]


def test_faq_items_can_be_reordered_from_the_list(admin_client):
    a = FaqItem.objects.create(question="a", answer="x", order=1)
    b = FaqItem.objects.create(question="b", answer="x", order=2)
    response = admin_client.post(url("faqitem", "changelist"), _reorder_post(a, b, 5, 2))
    assert response.status_code == 302
    assert list(FaqItem.objects.all()) == [b, a]


def test_expert_search_finds_by_specialty(admin_client):
    Expert.objects.create(name="a", degree="d", specialty="\u06af\u06cc\u0627\u0647\u200c\u067e\u0632\u0634\u06a9\u06cc")
    Expert.objects.create(name="b", degree="d", specialty="other")
    response = admin_client.get(url("expert", "changelist"), {"q": "\u06af\u06cc\u0627\u0647\u200c\u067e\u0632\u0634\u06a9\u06cc"})
    assert {e.name for e in response.context["cl"].result_list} == {"a"}
