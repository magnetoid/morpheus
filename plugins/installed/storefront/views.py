"""
Storefront Plugin — Views
Consumes the GraphQL API via internal_graphql(). Never touches ORM directly.
"""
from django.shortcuts import render, redirect
from api.client import internal_graphql


PRODUCT_LIST_QUERY = """
query ProductList($first: Int!, $search: String, $category: String) {
  products(first: $first, search: $search, category: $category) {
    id name slug price { amount currency }
    compareAtPrice { amount }
    primaryImage { url altText }
    isOnSale discountPercentage
    averageRating
  }
}
"""

PRODUCT_DETAIL_QUERY = """
query ProductDetail($slug: String!) {
  product(slug: $slug) {
    id name slug description shortDescription
    price { amount currency }
    compareAtPrice { amount }
    images { url altText isPrimary }
    variants { id name sku price { amount currency } isActive }
    tags category { name slug }
    averageRating
    reviews { rating title body customer { fullName } createdAt }
  }
}
"""

CART_QUERY = """
query Cart {
  cart {
    id itemCount subtotal { amount currency }
    items {
      id quantity unitPrice { amount currency } totalPrice { amount currency }
      product { name slug primaryImage { url } }
      variant { name sku }
    }
    coupon { code discountType discountValue }
  }
}
"""


def home(request):
    data = internal_graphql("""
        query Home {
          featuredProducts: products(first: 8, featured: true) {
            id name slug price { amount currency }
            primaryImage { url altText }
            isOnSale discountPercentage
          }
          collections(featured: true, first: 6) {
            id name slug image { url }
          }
          categories(topLevel: true, first: 8) {
            id name slug image { url }
          }
        }
    """, request=request) or {}
    # Templates use snake_case; GraphQL returns camelCase. Normalise.
    data.setdefault('featured_products', data.get('featuredProducts', []) or [])
    data.setdefault('seasonal_products', data.get('featured_products', []))
    return render(request, 'storefront/home.html', data)


def product_list(request):
    data = internal_graphql(PRODUCT_LIST_QUERY, variables={
        'first': 24,
        'search': request.GET.get('q', ''),
        'category': request.GET.get('category', ''),
    }, request=request)
    return render(request, 'storefront/product_list.html', {
        'products': (data or {}).get('products', []),
        'search_query': request.GET.get('q', ''),
    })


def product_detail(request, slug):
    data = internal_graphql(PRODUCT_DETAIL_QUERY, variables={'slug': slug}, request=request)
    product = (data or {}).get('product')
    if not product:
        from django.http import Http404
        raise Http404
    return render(request, 'storefront/product_detail.html', {'product': product})


def cart(request):
    data = internal_graphql(CART_QUERY, request=request)
    return render(request, 'storefront/cart.html', {'cart': (data or {}).get('cart', {})})


def checkout(request):
    if request.method == 'GET':
        return render(request, 'storefront/checkout.html')
    # POST — handled via GraphQL mutation from JS
    return redirect('storefront:cart')


def search(request):
    q = request.GET.get('q', '').strip()
    use_semantic = request.GET.get('mode') == 'semantic'

    if use_semantic and q:
        data = internal_graphql("""
            query SemanticSearch($query: String!) {
              semanticSearch(query: $query) {
                products { id name slug price { amount currency } primaryImage { url } }
                explanation
              }
            }
        """, variables={'query': q}, request=request)
        result = (data or {}).get('semanticSearch', {})
    else:
        data = internal_graphql(PRODUCT_LIST_QUERY, variables={
            'first': 24, 'search': q, 'category': ''
        }, request=request)
        result = {'products': (data or {}).get('products', []), 'explanation': None}

    return render(request, 'storefront/search.html', {
        'query': q, 'result': result, 'semantic': use_semantic
    })


# ─────────────────────────────────────────────────────────────────────────────
# Static + content pages
# ─────────────────────────────────────────────────────────────────────────────


# Hardcoded journal entries — TODO: extract to a CMS plugin with editable posts.
_JOURNAL_ENTRIES = [
    {
        'slug': 'a-short-note-on-patience',
        'title': 'A short note on patience and the long sentence',
        'date_label': 'April · 4 min read',
        'excerpt': 'On Cusk, on Sebald, on the way a long paragraph teaches you how to wait.',
        'body': (
            "There's a particular pleasure in a sentence that takes a breath you didn't know "
            "you had to give it. Cusk does this. Sebald does this. The reader is asked to slow "
            "down — to hold a thought in suspension — and in that suspension something settles. "
            "We carry a few of these books on the shelf this season because we believe in the "
            "case for the long take."
        ),
    },
    {
        'slug': 'why-we-dont-carry-books-we-havent-read',
        'title': "Why we don't carry books we haven't read",
        'date_label': 'April · 3 min read',
        'excerpt': 'A diary of how the shelf gets curated, and why it\'s a small one on purpose.',
        'body': (
            "Every title in the shop has been read by at least one of us before it makes it to "
            "the shelf. That's both a constraint and a promise. The constraint: the shop will "
            "always be small. The promise: if a book is here, it earned the spot. We trade "
            "breadth for trust."
        ),
    },
    {
        'slug': 'the-case-for-the-small-press',
        'title': 'The case for the small press, made in numbers',
        'date_label': 'April · 6 min read',
        'excerpt': 'Three years of receipts, and what they say about who\'s actually publishing the work that lasts.',
        'body': (
            "Pull three years of receipts and the picture is unambiguous: the books that customers "
            "come back to, the books they recommend to a friend, the books they buy a second copy "
            "of — they're disproportionately from independent presses. Not because indie is "
            "automatically better, but because the editors there have time to be wrong on purpose."
        ),
    },
]


def about(request):
    return render(request, 'storefront/about.html')


def contact(request):
    sent = False
    if request.method == 'POST':
        # Minimal: log the message and show a thank-you. A future contact plugin
        # can pipe these into CRM as Leads or Interactions.
        from plugins.installed.crm.services import upsert_lead, log_interaction
        from django.db import DatabaseError
        email = (request.POST.get('email') or '').strip().lower()
        name = (request.POST.get('name') or '').strip()
        body = (request.POST.get('message') or '').strip()
        if email and body:
            try:
                lead = upsert_lead(
                    email=email,
                    first_name=name.split(' ')[0] if name else '',
                    last_name=' '.join(name.split(' ')[1:]) if ' ' in name else '',
                    source='storefront',
                )
                log_interaction(
                    subject=lead, kind='note', direction='inbound',
                    summary='Contact form submission', body=body,
                    actor_name='storefront',
                )
            except (ImportError, DatabaseError):
                pass
        sent = True
    return render(request, 'storefront/contact.html', {'sent': sent})


def journal_index(request):
    return render(request, 'storefront/journal_index.html', {'entries': _JOURNAL_ENTRIES})


def journal_detail(request, slug):
    from django.http import Http404
    entry = next((e for e in _JOURNAL_ENTRIES if e['slug'] == slug), None)
    if entry is None:
        raise Http404
    return render(request, 'storefront/journal_detail.html', {'entry': entry})


def categories(request):
    data = internal_graphql("""
        query Categories {
          categories(topLevel: true, first: 50) {
            id name slug image { url }
          }
        }
    """, request=request) or {}
    return render(request, 'storefront/categories.html', {
        'categories': data.get('categories', []),
    })


def account_home(request):
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('/accounts/login/?next=/account/')
    return render(request, 'storefront/account_home.html', {
        'user': request.user,
    })


def account_orders(request):
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect('/accounts/login/?next=/account/orders/')
    try:
        from plugins.installed.orders.models import Order
        orders = list(
            Order.objects.filter(customer=request.user)
            .order_by('-created_at')[:50]
        )
    except Exception:  # noqa: BLE001
        orders = []
    return render(request, 'storefront/account_orders.html', {'orders': orders})


def account_order_detail(request, order_number):
    if not request.user.is_authenticated:
        from django.shortcuts import redirect
        return redirect(f'/accounts/login/?next=/account/orders/{order_number}/')
    from django.shortcuts import get_object_or_404
    from plugins.installed.orders.models import Order
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        order_number=order_number, customer=request.user,
    )
    return render(request, 'storefront/account_order_detail.html', {'order': order})


def order_confirmation(request, order_number):
    """Public order confirmation — accessible by order_number alone (signed link).
    Future: token-protect to prevent enumeration."""
    from django.shortcuts import get_object_or_404
    from plugins.installed.orders.models import Order
    order = get_object_or_404(
        Order.objects.prefetch_related('items'), order_number=order_number,
    )
    return render(request, 'storefront/order_confirmation.html', {'order': order})


def coming_soon(request, slug=None):
    """Generic placeholder for footer links that don't have first-class pages
    yet (stockists, staff picks, shipping, returns). One template, many paths."""
    title_map = {
        'stockists': 'Stockists',
        'staff-picks': 'Staff picks',
        'shipping': 'Shipping',
        'returns': 'Returns',
    }
    page_slug = slug or request.path.strip('/').split('/')[-1] or 'coming-soon'
    return render(request, 'storefront/coming_soon.html', {
        'page_title': title_map.get(page_slug, page_slug.replace('-', ' ').title()),
    })
