from django.utils.functional import SimpleLazyObject

from .models import Article


def articles_nav(request):
    """`has_articles` in every template: True once something is published (D11).

    Lazy, so the query runs only on a page that actually reads it (the header
    menu and the home page), and at most once per page.
    """
    return {"has_articles": SimpleLazyObject(lambda: Article.objects.published().exists())}
