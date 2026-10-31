"""The public product list (D39)."""
from django.shortcuts import render

from .models import Product, ProductType
from .search import search

# A longer query is cut, not refused: search() compares every word with every
# product, so there is no reason to let someone paste a page of text into it.
MAX_QUERY_LENGTH = 100


def product_list(request):
    """All products, narrowed by `?type=<slug>` and searched with `?q=<text>`.

    Unavailable products stay in the list (D7). With no query, available
    products come first, then alphabetically by trade name; when there is a
    query, search() ranks first and keeps this order inside each rank (D38).
    """
    query = request.GET.get("q", "").strip()[:MAX_QUERY_LENGTH]

    # Only types that have products: a chip that leads to an empty list is noise.
    types = list(ProductType.objects.filter(pk__in=Product.objects.values("product_type")))
    wanted = request.GET.get("type", "")
    # An unknown slug (an old bookmark, a deleted type) is ignored, not a 404.
    selected_type = next((t for t in types if t.slug == wanted), None)

    products = Product.objects.select_related("product_type").order_by("-is_available", "trade_name")
    if selected_type:
        products = products.filter(product_type=selected_type)

    results = search(query, products)
    return render(
        request,
        "catalog/product_list.html",
        {
            "products": results,
            "count": len(results),
            "types": types,
            "selected_type": selected_type,
            "q": query,
        },
    )
