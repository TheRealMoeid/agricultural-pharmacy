"""`{% load clicks %}`: the href for a tracked call/message button (D16/D44)."""
from urllib.parse import quote

from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def click_url(context, kind):
    """The href for a tracked button: `/click/<kind>/?from=<current page>`.

    `kind` is one of ClickEvent.Kind ("call", "whatsapp", "telegram",
    "rubika"). The current page's path is read from the request already in
    the template context (the `django.template.context_processors.request`
    processor is registered), not from the Referer header, which browsers
    often strip or block.
    """
    request = context.get("request")
    path = getattr(request, "path", "") if request is not None else ""
    return f"{reverse('core:track_click', args=[kind])}?from={quote(path)}"
