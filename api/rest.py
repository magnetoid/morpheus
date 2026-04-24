"""
Morpheus CMS — REST API v1
Versioned, filterable, channel-scoped storefront REST layer.
"""
from rest_framework import viewsets, serializers, filters
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from plugins.installed.catalog.models import Product, Category
from plugins.installed.orders.models import Order


# ── Serializers ───────────────────────────────────────────────────────────────

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description', 'is_active']


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ['id', 'name', 'slug', 'short_description', 'price', 'category',
                  'status', 'is_featured', 'created_at']

    def get_price(self, obj):
        if obj.price:
            return {'amount': str(obj.price.amount), 'currency': obj.price.currency.code}
        return {'amount': '0.00', 'currency': 'USD'}


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['id', 'order_number', 'status', 'payment_status', 'placed_at']


# ── ViewSets ─────────────────────────────────────────────────────────────────

class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/products/           — list active products
    GET /api/v1/products/{id}/      — single product
    GET /api/v1/products/?search=   — text search on name/description
    GET /api/v1/products/?category= — filter by category slug
    GET /api/v1/products/?featured= — filter featured only
    GET /api/v1/products/?ordering= — order by price, created_at, name
    """
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {'status': ['exact'], 'is_featured': ['exact'], 'category__slug': ['exact']}
    search_fields = ['name', 'short_description', 'description']
    ordering_fields = ['name', 'price', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.filter(status='active').select_related('category')

        # Multi-tenancy: scope to the requesting channel if an API key provides one
        request = self.request
        api_key = getattr(request, '_morpheus_api_key', None)
        if api_key and api_key.channel_id:
            qs = qs.filter(channels=api_key.channel)

        return qs


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/categories/         — list all active categories
    GET /api/v1/categories/{id}/    — single category with children
    """
    queryset = Category.objects.filter(is_active=True)
    serializer_class = CategorySerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    """
    GET /api/v1/orders/             — authenticated customer's own orders
    GET /api/v1/orders/{id}/        — single order detail
    """
    serializer_class = OrderSerializer

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return Order.objects.none()
        return Order.objects.filter(
            customer__user=self.request.user
        ).select_related('channel')
