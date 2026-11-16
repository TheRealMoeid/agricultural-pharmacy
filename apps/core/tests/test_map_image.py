import pytest

from django.contrib import admin as django_admin

from apps.core.fields import WebPImageField
from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


def test_map_image_field_parameters():
    field = SiteSettings._meta.get_field("map_image")
    assert isinstance(field, WebPImageField)
    assert field.max_side == 800
    assert field.max_bytes == 60000
    assert field.quality == 80
    assert field.thumb_side is None
    assert field.blank is True
    assert field.upload_to == "map/"


def test_map_image_optional(db):
    site = SiteSettings.load()
    assert not site.map_image


def test_admin_fieldset_includes_map_image():
    ma = django_admin.site._registry[SiteSettings]
    fields = [name for _title, opts in ma.fieldsets for name in opts["fields"]]
    assert "map_image" in fields