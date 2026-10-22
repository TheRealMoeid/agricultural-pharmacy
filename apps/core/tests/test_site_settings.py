import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command

from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


def test_load_creates_the_row_with_the_confirmed_defaults():
    assert SiteSettings.objects.count() == 0
    site = SiteSettings.load()
    assert SiteSettings.objects.count() == 1
    assert site.pk == 1
    assert site.phone == "09112747628"
    assert "گنبدکاووس" in site.address
    assert "جمعه" in site.working_hours
    assert site.notification_channel == SiteSettings.NotificationChannel.NONE
    assert site.show_farm_visit_fee is False


def test_load_returns_the_same_row_every_time():
    first = SiteSettings.load()
    first.store_name = "نام آزمایشی"
    first.save()
    assert SiteSettings.load().store_name == "نام آزمایشی"
    assert SiteSettings.objects.count() == 1


def test_a_second_instance_overwrites_instead_of_adding_a_row():
    SiteSettings.load()
    other = SiteSettings(store_name="فروشگاه دیگر")
    other.save()
    assert SiteSettings.objects.count() == 1
    assert SiteSettings.objects.get().store_name == "فروشگاه دیگر"


def test_derived_contact_links_from_the_default_number():
    site = SiteSettings.load()
    assert site.phone_display == "0911 274 7628"
    assert site.phone_international == "989112747628"
    assert site.tel_url == "tel:+989112747628"
    assert site.whatsapp_url == "https://wa.me/989112747628"


def test_phone_is_stored_in_the_canonical_form():
    site = SiteSettings.load()
    site.phone = "(+98)09112747628"
    site.full_clean()
    site.save()
    site.refresh_from_db()
    assert site.phone == "09112747628"


def test_persian_digits_in_the_phone_are_accepted():
    site = SiteSettings.load()
    site.phone = "\u06f0\u06f9\u06f1\u06f1\u06f2\u06f7\u06f4\u06f7\u06f6\u06f2\u06f8"
    site.full_clean()
    site.save()
    assert SiteSettings.objects.get().phone == "09112747628"


def test_invalid_phone_is_rejected():
    site = SiteSettings.load()
    site.phone = "12345"
    with pytest.raises(ValidationError) as exc:
        site.full_clean()
    assert "phone" in exc.value.message_dict


def test_telegram_button_is_hidden_until_a_username_is_set():
    site = SiteSettings.load()
    assert site.telegram_url == ""
    site.telegram_username = "@Ghayyadi_store"
    site.full_clean()
    site.save()
    site.refresh_from_db()
    assert site.telegram_username == "Ghayyadi_store"
    assert site.telegram_url == "https://t.me/Ghayyadi_store"


@pytest.mark.parametrize("bad", ["ab", "1starts_with_digit", "has space", "bad-dash", "x" * 40])
def test_invalid_telegram_usernames_are_rejected(bad):
    site = SiteSettings.load()
    site.telegram_username = bad
    with pytest.raises(ValidationError) as exc:
        site.full_clean()
    assert "telegram_username" in exc.value.message_dict


def test_rubika_is_stored_as_the_pasted_link_and_must_be_a_url():
    site = SiteSettings.load()
    site.rubika_url = "not a link"
    with pytest.raises(ValidationError) as exc:
        site.full_clean()
    assert "rubika_url" in exc.value.message_dict
    site.rubika_url = "https://rubika.ir/example"
    site.full_clean()


def test_fee_is_visible_only_when_switched_on_and_text_is_present():
    site = SiteSettings.load()
    site.farm_visit_fee_text = "۵۰۰ هزار تومان"
    assert site.farm_visit_fee_visible is False  # text, but switch off
    site.show_farm_visit_fee = True
    assert site.farm_visit_fee_visible is True
    site.farm_visit_fee_text = "   "
    assert site.farm_visit_fee_visible is False  # switch on, but nothing to show


def test_migrations_are_in_sync_with_the_models():
    # Fails if a model change was made without creating its migration.
    call_command("makemigrations", "--check", "--dry-run")
