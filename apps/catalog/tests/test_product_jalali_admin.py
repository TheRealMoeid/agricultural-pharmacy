"""Tests that ProductAdmin actually uses JalaliDateField for its date fields."""
import datetime

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from apps.catalog.models import Product
from apps.core.jalali import jalali_to_gregorian

pytestmark = pytest.mark.django_db


@pytest.fixture
def admin_client():
    user = get_user_model().objects.create_superuser("boss", "boss@example.com", "pw-for-tests-123")
    client = Client()
    client.force_login(user)
    return client


def url(view, *args):
    return reverse(f"admin:catalog_product_{view}", args=args)


def post_data(product_fields, **overrides):
    data = {k: (v.pk if k == "product_type" else v) for k, v in product_fields.items()}
    data.update(usage="", dosage="", timing="", production_date="", expiry_date="", crops=[], pests=[])
    data.update(overrides)
    return data


def test_a_jalali_date_typed_in_the_admin_is_stored_as_gregorian(admin_client, product_fields):
    data = post_data(product_fields, production_date="1403/01/01")
    response = admin_client.post(url("add"), data)
    assert response.status_code == 302, getattr(
        getattr(response, "context", None), "get", lambda *_: None
    )("adminform")
    product = Product.objects.get()
    assert product.production_date == datetime.date(2024, 3, 20)


def test_an_existing_product_shows_its_date_in_jalali_on_the_change_form(admin_client, product_fields):
    product = Product.objects.create(
        **product_fields, production_date=datetime.date(2024, 3, 20)
    )
    html = admin_client.get(url("change", product.pk)).content.decode()
    assert "1403/01/01" in html
    assert "2024-03-20" not in html


def test_an_invalid_jalali_date_is_rejected_with_a_persian_message(admin_client, product_fields):
    data = post_data(product_fields, production_date="not a date")
    response = admin_client.post(url("add"), data)
    assert response.status_code == 200
    assert Product.objects.count() == 0
    assert "تاریخ را به صورت" in response.content.decode()


def test_a_calendar_date_that_does_not_exist_is_rejected(admin_client, product_fields):
    # 1402 is not a leap year, so Esfand only has 29 days.
    data = post_data(product_fields, production_date="1402/12/30")
    response = admin_client.post(url("add"), data)
    assert response.status_code == 200
    assert Product.objects.count() == 0
    assert "وجود ندارد" in response.content.decode()


def test_leaving_both_dates_empty_is_still_fine(admin_client, product_fields):
    response = admin_client.post(url("add"), post_data(product_fields))
    assert response.status_code == 302
    product = Product.objects.get()
    assert product.production_date is None
    assert product.expiry_date is None


def test_expiry_before_production_is_still_rejected_when_typed_in_jalali(admin_client, product_fields):
    data = post_data(
        product_fields,
        production_date="1403/06/01",
        expiry_date="1403/01/01",  # earlier than production
    )
    response = admin_client.post(url("add"), data)
    assert response.status_code == 200
    assert Product.objects.count() == 0
    assert "باید بعد از تاریخ تولید باشد" in response.content.decode()


def test_round_trip_a_date_through_an_edit(admin_client, product_fields):
    product = Product.objects.create(**product_fields)
    data = post_data(product_fields, production_date="1404/02/10")
    response = admin_client.post(url("change", product.pk), data)
    assert response.status_code == 302
    product.refresh_from_db()
    assert product.production_date == jalali_to_gregorian(1404, 2, 10)
