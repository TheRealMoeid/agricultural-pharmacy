import pytest
from django.template import RequestContext, Template
from django.test import RequestFactory

from apps.core.context_processors import site_settings
from apps.core.models import SiteSettings

pytestmark = pytest.mark.django_db


def test_the_processor_returns_the_settings_row():
    request = RequestFactory().get("/")
    assert site_settings(request)["site"] == SiteSettings.load()


def test_templates_get_the_site_variable_without_the_view_passing_it():
    # Goes through the real TEMPLATES setting, so it fails if the processor is not registered.
    request = RequestFactory().get("/")
    template = Template("{{ site.phone_display }}|{{ site.tel_url }}")
    rendered = template.render(RequestContext(request))
    assert rendered == "0911 274 7628|tel:+989112747628"
