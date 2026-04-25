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
