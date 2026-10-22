from .models import SiteSettings


def site_settings(request):
    """Make the store settings available in every template as `site`."""
    return {"site": SiteSettings.load()}
