import strawberry
from typing import List, Optional
from plugins.installed.catalog.models import Product, Category
from plugins.installed.catalog.graphql.types import ProductType, CategoryType

@strawberry.type
class CatalogQueryExtension:
    
    @strawberry.field(description="Get a single product by its slug")
    def product(self, slug: str) -> Optional[ProductType]:
        try:
            return Product.objects.get(slug=slug, status='active')
        except Product.DoesNotExist:
            return None

    @strawberry.field(description="Get a list of active products")
    def products(self, first: int = 50, is_featured: Optional[bool] = None) -> List[ProductType]:
        qs = Product.objects.filter(status='active')
        if is_featured is not None:
            qs = qs.filter(is_featured=is_featured)
        return list(qs[:first])

    @strawberry.field(description="Get a list of all active categories")
    def categories(self) -> List[CategoryType]:
        return list(Category.objects.filter(is_active=True))
