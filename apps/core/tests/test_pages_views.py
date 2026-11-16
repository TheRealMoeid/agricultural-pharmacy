import pytest
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.pages.models import Expert

pytestmark = pytest.mark.django_db


@pytest.fixture
def experts(db):
    Expert.objects.create(
        name="کارشناس یک",
        degree="مدرک یک",
        role="سمت یک",
        experience="سابقه یک",
        order=1,
    )
    Expert.objects.create(
        name="کارشناس دو",
        degree="مدرک دو",
        specialty="تخصص دو",
        order=2,
    )


def test_home_links_to_experts_and_contact(client):
    res = client.get(reverse("pages:home"))
    assert res.status_code == 200
    content = res.content.decode()
    assert reverse("pages:experts") in content
    assert reverse("pages:contact") in content


def test_experts_renders_in_order_with_filled_fields(client, experts):
    content = client.get(reverse("pages:experts")).content.decode()
    one = content.index("کارشناس یک")
    two = content.index("کارشناس دو")
    assert one < two
    assert "مدرک یک" in content
    assert "سمت یک" in content
    assert "سابقه یک" in content
    assert "تخصص دو" in content


def test_experts_hides_blank_fields(client, experts):
    content = client.get(reverse("pages:experts")).content.decode()
    second_card = content.split("کارشناس دو", 1)[1]
    assert "سابقه" not in second_card
    assert "سمت" not in second_card


def test_experts_placeholder_when_no_photo(client, experts):
    content = client.get(reverse("pages:experts")).content.decode()
    assert "<svg" in content


def test_experts_empty_state(client, db):
    content = client.get(reverse("pages:experts")).content.decode()
    assert "اطلاعات کارشناسان" in content
    assert reverse("consultations:form") in content


def test_experts_query_count(client, experts, django_assert_num_queries):
    SiteSettings.load()  # create the row here, outside the counted block
    with django_assert_num_queries(2):
        client.get(reverse("pages:experts"))


def test_contact_shows_phone_address_hours(client):
    site = SiteSettings.load()
    content = client.get(reverse("pages:contact")).content.decode()
    assert site.phone_display in content
    assert site.address in content
    assert site.working_hours in content


def test_contact_whatsapp_button(client):
    content = client.get(reverse("pages:contact")).content.decode()
    assert "واتساپ" in content
    assert "wa.me" in content


def test_contact_telegram_hidden_without_username(client):
    site = SiteSettings.load()
    site.telegram_username = ""
    site.save()
    content = client.get(reverse("pages:contact")).content.decode()
    assert "تلگرام" not in content


def test_contact_telegram_shown_with_username(client):
    site = SiteSettings.load()
    site.telegram_username = "store_test"
    site.save()
    content = client.get(reverse("pages:contact")).content.decode()
    assert "تلگرام" in content
    assert "t.me/store_test" in content


def test_contact_rubika_hidden_without_link(client):
    content = client.get(reverse("pages:contact")).content.decode()
    assert "روبیکا" not in content


def test_contact_map_block_hidden_when_empty(client):
    content = client.get(reverse("pages:contact")).content.decode()
    assert "نقشه موقعیت فروشگاه" not in content
    assert "نقشه گوگل" not in content


def test_contact_map_links_shown(client):
    site = SiteSettings.load()
    site.google_maps_url = "https://maps.google.com/?q=test"
    site.iranian_map_name = "نشان"
    site.iranian_map_url = "https://nshn.ir/test"
    site.save()
    content = client.get(reverse("pages:contact")).content.decode()
    assert "نقشه گوگل" in content
    assert "نشان" in content


def test_contact_iranian_map_needs_name_and_url(client):
    site = SiteSettings.load()
    site.iranian_map_url = "https://nshn.ir/test"
    site.save()
    content = client.get(reverse("pages:contact")).content.decode()
    assert "nshn.ir" not in content