import strawberry
import strawberry_django
from typing import List, Optional
from plugins.installed.orders import models
from core.graphql.types import MoneyType

@strawberry_django.type(models.OrderItem)
class OrderItemType:
    id: strawberry.ID
    product_name: str
    variant_name: str
    sku: str
    quantity: int
    
    @strawberry.field
    def unit_price(self) -> MoneyType:
        return MoneyType(amount=str(self.unit_price.amount), currency=str(self.unit_price.currency))

    @strawberry.field
    def total_price(self) -> MoneyType:
        return MoneyType(amount=str(self.total_price.amount), currency=str(self.total_price.currency))

@strawberry_django.type(models.Order)
class OrderType:
    id: strawberry.ID = strawberry.field(description="Unique order identifier")
    order_number: str = strawberry.field(description="Human readable order number")
    email: str = strawberry.field(description="Customer email")
    status: str = strawberry.field(description="Order status: pending, confirmed, processing, shipped, etc.")
    
    @strawberry.field
    def subtotal(self) -> MoneyType:
        return MoneyType(amount=str(self.subtotal.amount), currency=str(self.subtotal.currency))

    @strawberry.field
    def total(self) -> MoneyType:
        return MoneyType(amount=str(self.total.amount), currency=str(self.total.currency))
        
    items: List[OrderItemType] = strawberry.field(description="Items purchased in this order")

@strawberry_django.type(models.CartItem)
class CartItemType:
    id: strawberry.ID
    quantity: int

    @strawberry.field
    def unit_price(self) -> MoneyType:
        return MoneyType(amount=str(self.unit_price.amount), currency=str(self.unit_price.currency))

@strawberry_django.type(models.Cart)
class CartType:
    id: strawberry.ID = strawberry.field(description="Cart identifier")
    session_key: str = strawberry.field(description="Session key for anonymous carts")
    items: List[CartItemType] = strawberry.field(description="Items in the cart")
