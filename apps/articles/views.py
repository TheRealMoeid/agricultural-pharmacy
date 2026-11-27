"""The public articles pages (D46): the list at /articles/ and one article at /articles/<slug>/.

Only published articles are ever shown (`Article.objects.published()`, D34).
A draft is simply not found, the same as a slug that never existed.
"""
import re

from django.shortcuts import render

from .models import Article

# A blank line (possibly with spaces on it) starts a new paragraph (D34).
_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def split_paragraphs(body: str) -> list[str]:
    """The body as a list of paragraphs. Single line breaks inside one are kept."""
    return [part.strip() for part in _PARAGRAPH_BREAK.split(body or "") if part.strip()]


def article_list(request):
    """Published articles, newest first, optionally narrowed with `?season=<value>`.

    One query: the whole (short) list is loaded without the bodies, and both the
    season chips and the season filter are worked out from it in Python. A season
    with no published article is not offered, and an unknown or unoffered one is
    ignored, not a 404. No pagination: the experts write a few articles a year.
    """
    articles = list(Article.objects.published().defer("body"))
    present = {article.season for article in articles}
    seasons = [(value, label) for value, label in Article.Season.choices if value in present]

    wanted = request.GET.get("season", "")
    selected = next((value for value, _ in seasons if value == wanted), None)
    if selected:
        articles = [article for article in articles if article.season == selected]

    return render(
        request,
        "articles/article_list.html",
        {"articles": articles, "seasons": seasons, "selected_season": selected},
    )


def article_detail(request, slug):
    """One published article. A draft or a missing slug gets the friendly not-found page (404)."""
    article = Article.objects.published().filter(slug=slug).first()
    if article is None:
        return render(request, "articles/article_not_found.html", status=404)
    return render(
        request,
        "articles/article_detail.html",
        {"article": article, "paragraphs": split_paragraphs(article.body)},
    )
