import strawberry
from typing import List, Optional
from plugins.installed.orders.models import Order, Cart
from plugins.installed.orders.graphql.types import OrderType, CartType

@strawberry.type
class OrdersQueryExtension:
    
    @strawberry.field(description="Get an order by its order number")
    def order(self, order_number: str) -> Optional[OrderType]:
        try:
            return Order.objects.get(order_number=order_number)
        except Order.DoesNotExist:
            return None

    @strawberry.field(description="Get a list of orders (can be used by admin or filtered by customer)")
    def orders(self, first: int = 50, order_by: str = "-placed_at") -> List[OrderType]:
        # For now we just return all orders since we haven't implemented full permissions
        qs = Order.objects.all().order_by(order_by)
        return list(qs[:first])

    @strawberry.field(description="Get a cart by its ID")
    def cart(self, id: strawberry.ID) -> Optional[CartType]:
        try:
            return Cart.objects.get(id=id)
        except Cart.DoesNotExist:
            return None
