"""Shared fixtures for the catalog tests."""
import io

import pytest
from PIL import Image

from apps.catalog.models import Crop, Pest, ProductType


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    """Uploaded photos go to a throwaway folder, never into the real media/."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def product_type(db):
    return ProductType.objects.create(name="\u0642\u0627\u0631\u0686\u200c\u06a9\u0634")  # قارچ‌کش


@pytest.fixture
def crop(db):
    return Crop.objects.create(name="\u06af\u0646\u062f\u0645")  # گندم


@pytest.fixture
def pest(db):
    return Pest.objects.create(name="\u0633\u0646")  # سن


@pytest.fixture
def product_fields(product_type):
    """The minimum fields a valid Product needs, as a plain dict."""
    return dict(
        trade_name="\u0627\u0633\u06a9\u0648\u0631",  # اسکور
        generic_name="\u062f\u06cc\u0641\u0646\u0648\u06a9\u0648\u0646\u0627\u0632\u0648\u0644",  # دیفنوکونازول
        product_type=product_type,
        manufacturer="\u0634\u0631\u06a9\u062a \u0627\u0644\u0641",  # شرکت الف
        importer="\u0634\u0631\u06a9\u062a \u0628",  # شرکت ب
        country_of_origin="\u0622\u0644\u0645\u0627\u0646",  # آلمان
    )


def make_image_bytes(fmt="PNG", color="green", size=(10, 10)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format=fmt)
    return buf.getvalue()
