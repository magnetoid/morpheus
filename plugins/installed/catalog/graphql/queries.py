import strawberry
from typing import List, Optional

from django.db.models import Q

from api.graphql_permissions import current_channel_id
from plugins.installed.catalog.graphql.types import (
    CategoryType,
    CollectionType,
    ProductType,
)
from plugins.installed.catalog.models import Category, Collection, Product

_PRODUCT_RELATED = ('category', 'vendor')
_PRODUCT_PREFETCH = ('variants', 'images', 'tags', 'collections')

_MAX_FIRST = 100
_MAX_SEARCH_LEN = 100


def _clamp_first(first: int) -> int:
    return max(1, min(first, _MAX_FIRST))


def _scope_to_channel(qs, info):
    channel_id = current_channel_id(info)
    if channel_id:
        qs = qs.filter(channels=channel_id)
    return qs


@strawberry.type
class CatalogQueryExtension:

    @strawberry.field(description="Get a single product by its slug")
    def product(self, info: strawberry.Info, slug: str) -> Optional[ProductType]:
        qs = (
            Product.objects.filter(status='active', slug=slug)
            .select_related(*_PRODUCT_RELATED)
            .prefetch_related(*_PRODUCT_PREFETCH)
        )
        qs = _scope_to_channel(qs, info)
        return qs.first()

    @strawberry.field(description="Get a list of active products")
    def products(
        self,
        info: strawberry.Info,
        first: int = 50,
        featured: Optional[bool] = None,
        search: Optional[str] = None,
        category: Optional[str] = None,
    ) -> List[ProductType]:
        first = _clamp_first(first)

        qs = (
            Product.objects.filter(status='active')
            .select_related(*_PRODUCT_RELATED)
            .prefetch_related(*_PRODUCT_PREFETCH)
        )
        qs = _scope_to_channel(qs, info)

        if featured is not None:
            qs = qs.filter(is_featured=featured)
        if search:
            search = search.strip()[:_MAX_SEARCH_LEN]
            if search:
                qs = qs.filter(
                    Q(name__icontains=search)
                    | Q(short_description__icontains=search)
                    | Q(tags__name__icontains=search)
                ).distinct()
        if category:
            qs = qs.filter(category__slug=category)

        return list(qs[:first])

    @strawberry.field(description="Get a list of active collections")
    def collections(
        self,
        info: strawberry.Info,
        first: int = 50,
        featured: Optional[bool] = None,
    ) -> List[CollectionType]:
        first = _clamp_first(first)
        qs = Collection.objects.filter(is_active=True)
        if featured is not None:
            qs = qs.filter(is_featured=featured)
        return list(qs.order_by('sort_order', 'name')[:first])

    @strawberry.field(description="Get a list of all active categories")
    def categories(
        self,
        info: strawberry.Info,
        first: int = 50,
        top_level: Optional[bool] = None,
    ) -> List[CategoryType]:
        first = _clamp_first(first)
        qs = Category.objects.filter(is_active=True).select_related('parent')
        if top_level:
            qs = qs.filter(parent__isnull=True)
        return list(qs[:first])
