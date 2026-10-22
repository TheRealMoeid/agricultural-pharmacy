import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


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


def test_the_list_page_goes_straight_to_the_single_row(admin_client):
    response = admin_client.get(reverse("admin:core_sitesettings_changelist"))
    site = SiteSettings.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("admin:core_sitesettings_change", args=[site.pk])


def test_the_edit_page_renders_in_persian(admin_client):
    site = SiteSettings.load()
    response = admin_client.get(reverse("admin:core_sitesettings_change", args=[site.pk]))
    html = response.content.decode()
    assert response.status_code == 200
    assert "شماره تماس" in html
    assert "نام کاربری تلگرام" in html


def test_saving_through_the_admin_normalizes_and_stores(admin_client):
    site = SiteSettings.load()
    url = reverse("admin:core_sitesettings_change", args=[site.pk])
    data = {
        "store_name": site.store_name,
        "address": site.address,
        "working_hours": site.working_hours,
        "phone": "+98 911 274 7628",
        "telegram_username": "@store_bot",
        "rubika_url": "",
        "google_maps_url": "",
        "iranian_map_name": "",
        "iranian_map_url": "",
        "notification_channel": "none",
        "farm_visit_fee_text": "",
    }
    response = admin_client.post(url, data)
    assert response.status_code == 302
    site.refresh_from_db()
    assert site.phone == "09112747628"
    assert site.telegram_username == "store_bot"


def test_no_second_row_and_no_delete(admin_client):
    site = SiteSettings.load()
    add = admin_client.get(reverse("admin:core_sitesettings_add"))
    assert add.status_code == 403
    delete = admin_client.get(reverse("admin:core_sitesettings_delete", args=[site.pk]))
    assert delete.status_code == 403


def test_staff_without_permission_cannot_open_it(staff_client):
    response = staff_client.get(reverse("admin:core_sitesettings_changelist"))
    assert response.status_code == 403
