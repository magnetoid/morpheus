"""
Morpheus CMS — API URLs (versioned)
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from api.rest import ProductViewSet, CategoryViewSet, OrderViewSet

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='product')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'orders', OrderViewSet, basename='order')


def graphql_view():
    from strawberry.django.views import GraphQLView
    from api.schema import get_schema
    return GraphQLView.as_view(schema=get_schema())


urlpatterns = [
    path('graphql/', graphql_view(), name='graphql'),
    # REST is versioned — allows us to ship /v2/ without breaking existing clients
    path('v1/', include(router.urls)),
    # Keep legacy /rest/ alias for backward compat during transition
    path('rest/', include(router.urls)),
]
