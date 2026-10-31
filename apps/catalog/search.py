"""The public product search (D38): Persian-aware, word by word, ranked.

A query is split into words, and every word has to match the product
somewhere -- its trade name, its generic name, its usage text, or the name or
an alternate name of one of its crops or pests -- the same "every word has to
match" rule the admin search already uses (`ReferenceAdmin.get_search_results`
in `apps/catalog/admin.py`, and `ConsultationRequestAdmin`'s). Typing style
does not matter: letters, digits, the half space and the forms of alef are
all normalized with `normalize_for_search()` (`apps/core/text.py`), on both
sides, the same way the reference lists already store and compare names.

`Product` itself stores no search key (decided in phase 1, task 7, and noted
again in `docs/ARCHITECTURE.md` section 8): matching several text fields and
two related lists at once does not fit one stored column well. With the
catalog's expected size, 50 to 200 products, matching in Python after loading
the products (with their crops and pests prefetched, so this stays one query
per model, not one per product) is simple, easy to get right for
`normalize_for_search()`'s fuller rules (alef folding, digit normalization),
and fast enough; there is no need for a database-level search index here.

Results are ranked, not just filtered, so a search for a product by its own
name is not buried under products that only happen to mention the same word
in their usage text or share one of its crops or pests:

    RANK_NAME    a query word matched the trade name or the generic name
    RANK_USAGE   no word matched the name, but one matched the usage text
    RANK_TAG     every match came from a crop's or a pest's name or
                 an alternate name

A product's rank is its best tier: if any query word matches the name, the
product ranks as RANK_NAME even if another word of the same query only
matched in the usage text or a crop/pest name. Within a rank, products keep
`Product`'s own ordering (alphabetical by trade name).

`search()` takes an optional starting queryset, so a caller can filter by
product type or availability first and search within that -- the product
list view (phase 2, task 3) will do exactly this for the type filter.
"""
from apps.core.text import normalize_for_search

from .models import Product

RANK_NAME = 0
RANK_USAGE = 1
RANK_TAG = 2


def _query_words(query: str) -> list[str]:
    """`query`, split into non-empty normalized words. Empty for a blank query."""
    words = []
    for word in (query or "").split():
        key = normalize_for_search(word)
        if key:
            words.append(key)
    return words


def _tag_keys(product: Product) -> set[str]:
    keys = set()
    for crop in product.crops.all():
        keys.update(crop.search_keys())
    for pest in product.pests.all():
        keys.update(pest.search_keys())
    return keys


def _rank(product: Product, words: list[str]) -> int | None:
    """`product`'s rank for `words`, or None if some word matches nowhere."""
    name_key = normalize_for_search(f"{product.trade_name} {product.generic_name}")
    usage_key = normalize_for_search(product.usage)
    tag_keys = _tag_keys(product)

    matched_name = matched_usage = matched_tag = False
    for word in words:
        in_name = word in name_key
        in_usage = word in usage_key
        in_tag = any(word in key for key in tag_keys)
        if not (in_name or in_usage or in_tag):
            return None
        matched_name = matched_name or in_name
        matched_usage = matched_usage or in_usage
        matched_tag = matched_tag or in_tag

    if matched_name:
        return RANK_NAME
    if matched_usage:
        return RANK_USAGE
    assert matched_tag  # every word matched somewhere, and not name or usage
    return RANK_TAG


def search(query: str, products=None) -> list[Product]:
    """Products in `products` (default: every product) matching every word of `query`.

    An empty or whitespace-only query matches everything, in `Product`'s own
    order -- the same as an empty admin search box. Otherwise the result is
    ranked: see the module docstring. `products` lets a caller narrow the
    search beforehand (by type, by availability, ...); it is searched exactly
    as given, so pass `Product.objects.all()` (the default) to search the
    whole catalog.
    """
    if products is None:
        products = Product.objects.all()
    words = _query_words(query)
    products = products.prefetch_related("crops", "pests")
    if not words:
        return list(products)
    ranked = []
    for product in products:
        rank = _rank(product, words)
        if rank is not None:
            ranked.append((rank, product))
    ranked.sort(key=lambda pair: pair[0])
    return [product for _, product in ranked]
