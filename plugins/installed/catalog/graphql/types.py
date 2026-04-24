import strawberry
from typing import Optional, List
import strawberry_django
from plugins.installed.catalog import models

@strawberry_django.type(models.Category)
class CategoryType:
    id: strawberry.ID = strawberry.field(description="Unique category identifier (UUID)")
    name: str = strawberry.field(description="Category display name")
    slug: str = strawberry.field(description="URL-safe identifier for deep linking")
    description: str = strawberry.field(description="Category description text")
    is_active: bool = strawberry.field(description="Whether this category is active")

@strawberry_django.type(models.AttributeGroup)
class AttributeGroupType:
    id: strawberry.ID
    name: str
    slug: str

@strawberry_django.type(models.Attribute)
class AttributeType:
    id: strawberry.ID
    name: str
    slug: str
    input_type: str
    is_variant: bool
    is_filterable: bool

@strawberry_django.type(models.AttributeValue)
class AttributeValueType:
    id: strawberry.ID
    name: str
    slug: str
    value: str

from core.graphql.types import MoneyType

@strawberry_django.type(models.ProductVariant)
class ProductVariantType:
    id: strawberry.ID = strawberry.field(description="Unique variant identifier (UUID)")
    name: str = strawberry.field(description="Variant name")
    sku: str = strawberry.field(description="Stock Keeping Unit")
    is_active: bool = strawberry.field(description="Whether this variant is active")

    @strawberry.field(description="Price of the variant")
    def price(self) -> Optional[MoneyType]:
        if not self.price:
            return None
        return MoneyType(amount=str(self.price.amount), currency=str(self.price.currency))

@strawberry_django.type(models.Product)
class ProductType:
    id: strawberry.ID = strawberry.field(description="Unique product identifier (UUID)")
    name: str = strawberry.field(description="Product display name")
    slug: str = strawberry.field(description="URL-safe identifier for deep linking")
    sku: str = strawberry.field(description="Stock Keeping Unit for simple products")
    product_type: str = strawberry.field(description="simple, variable, digital, bundle")
    status: str = strawberry.field(description="draft, active, archived")
    short_description: str = strawberry.field(description="Short summary description")
    description: str = strawberry.field(description="Full HTML or Markdown description")
    is_featured: bool = strawberry.field(description="Whether this product is featured")
    category: Optional[CategoryType] = strawberry.field(description="Primary category")
    variants: List[ProductVariantType] = strawberry.field(description="Available variants if variable product")

    @strawberry.field(description="Base price of the product")
    def price(self) -> MoneyType:
        return MoneyType(amount=str(self.price.amount), currency=str(self.price.currency))

    @strawberry.field(description="Compare at price (original price before discount)")
    def compare_at_price(self) -> Optional[MoneyType]:
        if not self.compare_at_price:
            return None
        return MoneyType(amount=str(self.compare_at_price.amount), currency=str(self.compare_at_price.currency))
