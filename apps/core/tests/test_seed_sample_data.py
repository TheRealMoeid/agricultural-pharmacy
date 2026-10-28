"""Tests for the seed_sample_data command."""
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.articles.models import Article
from apps.catalog.models import Crop, Pest, Product, ProductType
from apps.consultations.models import ConsultationRequest
from apps.core.management.commands.seed_sample_data import SAMPLE
from apps.pages.models import Expert, FaqItem

pytestmark = pytest.mark.django_db

ALL = [
    (ProductType, "name"),
    (Crop, "name"),
    (Pest, "name"),
    (Product, "trade_name"),
    (Expert, "name"),
    (FaqItem, "question"),
    (Article, "title"),
    (ConsultationRequest, "name"),
]


@pytest.fixture(autouse=True)
def debug_on(settings):
    settings.DEBUG = True  # pytest-django turns it off; the command needs it on


def run(*args):
    out = StringIO()
    call_command("seed_sample_data", *args, stdout=out)
    return out.getvalue()


def counts():
    return {model.__name__: model.objects.count() for model, _ in ALL}


# --- safety --------------------------------------------------------------------------------


@pytest.mark.parametrize("args", [(), ("--clear",)])
def test_it_refuses_to_run_without_debug(settings, args):
    settings.DEBUG = False
    with pytest.raises(CommandError) as exc:
        run(*args)
    assert "DEBUG" in str(exc.value)
    assert sum(counts().values()) == 0


def test_every_row_it_creates_is_marked_as_a_sample():
    run()
    for model, field in ALL:
        names = list(model.objects.values_list(field, flat=True))
        assert names, model
        assert all(name.startswith(SAMPLE) for name in names), model


def test_the_customers_in_the_sample_data_have_made_up_numbers():
    run()
    phones = set(ConsultationRequest.objects.values_list("phone", flat=True))
    assert phones == {"09000000001", "09000000002", "09000000003", "09000000004"}


# --- loading -------------------------------------------------------------------------------


def test_it_loads_the_expected_amounts_and_says_so():
    output = run()
    assert counts() == {
        "ProductType": 3,
        "Crop": 4,
        "Pest": 4,
        "Product": 12,
        "Expert": 2,
        "FaqItem": 3,
        "Article": 4,
        "ConsultationRequest": 4,
    }
    assert "Loaded 12 products" in output


def test_running_it_twice_does_not_duplicate_anything():
    run()
    first = counts()
    run()
    assert counts() == first


def test_running_it_again_puts_changed_sample_rows_back():
    run()
    product = Product.objects.get(trade_name__startswith=SAMPLE, is_available=False, trade_name__endswith="\u06f3")
    product.is_available = True
    product.save()
    run()
    product.refresh_from_db()
    assert product.is_available is False


def test_every_row_passes_the_models_own_validation():
    run()
    for model, _ in ALL:
        for obj in model.objects.all():
            obj.full_clean()


def test_the_data_covers_the_cases_the_pages_will_have_to_handle():
    run()
    assert Product.objects.filter(is_available=False).exists()
    assert Product.objects.filter(is_available=True).exists()
    assert Product.objects.filter(production_date__isnull=True, expiry_date__isnull=True).exists()
    assert Product.objects.filter(production_date__isnull=False, expiry_date__isnull=False).exists()
    assert Product.objects.filter(crops__isnull=True).exists()
    assert Product.objects.filter(pests__isnull=True).exists()
    # An expert like Habibollah (no role, no experience) and one like Rahmatollah.
    assert Expert.objects.filter(role="", experience="").exclude(specialty="").exists()
    assert Expert.objects.exclude(experience="").exclude(role="").exists()
    # The articles section: published and draft, all four seasons.
    assert Article.objects.filter(is_published=True).exists()
    assert Article.objects.filter(is_published=False).exists()
    assert set(Article.objects.values_list("season", flat=True)) == set(Article.Season.values)
    # The inbox: both kinds, both states.
    assert set(ConsultationRequest.objects.values_list("kind", flat=True)) == set(ConsultationRequest.Kind.values)
    assert set(ConsultationRequest.objects.values_list("status", flat=True)) == set(ConsultationRequest.Status.values)


def test_no_photos_are_created(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    run()
    assert list(tmp_path.iterdir()) == []


# --- clearing ------------------------------------------------------------------------------


def test_clear_removes_the_sample_rows_and_nothing_else():
    real_type = ProductType.objects.create(name="\u0642\u0627\u0631\u0686\u200c\u06a9\u0634")
    real_crop = Crop.objects.create(name="\u06af\u0646\u062f\u0645")
    real_expert = Expert.objects.create(name="\u0648\u0627\u0642\u0639\u06cc", degree="d")
    real_product = Product.objects.create(
        trade_name="\u0627\u0633\u06a9\u0648\u0631", generic_name="g", product_type=real_type,
        manufacturer="m", importer="i", country_of_origin="c",
    )
    real_product.crops.add(real_crop)
    run()
    output = run("--clear")
    assert "Removed 12 products" in output
    assert list(ProductType.objects.all()) == [real_type]
    assert list(Crop.objects.all()) == [real_crop]
    assert list(Expert.objects.all()) == [real_expert]
    assert list(Product.objects.all()) == [real_product]
    assert list(real_product.crops.all()) == [real_crop]
    for model in (Pest, FaqItem, Article, ConsultationRequest):
        assert model.objects.count() == 0


def test_clear_on_an_empty_database_is_fine():
    assert "Removed 0 products" in run("--clear")


def test_it_can_be_loaded_again_after_clearing():
    run()
    run("--clear")
    run()
    assert Product.objects.count() == 12


def test_clear_stops_and_removes_nothing_if_a_real_product_uses_a_sample_type():
    run()
    sample_type = ProductType.objects.filter(name__startswith=SAMPLE).first()
    Product.objects.create(
        trade_name="real", generic_name="g", product_type=sample_type,
        manufacturer="m", importer="i", country_of_origin="c",
    )
    before = counts()
    with pytest.raises(CommandError) as exc:
        run("--clear")
    assert "Nothing was removed" in str(exc.value)
    assert counts() == before
