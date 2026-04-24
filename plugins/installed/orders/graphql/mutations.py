import strawberry
from typing import Optional
from plugins.installed.orders.graphql.types import CartType
from core.graphql.types import ErrorType

from plugins.installed.orders.services import CartService

@strawberry.input
class AddToCartInput:
    product_id: str = strawberry.field(description="UUID of the product")
    quantity: int = strawberry.field(description="Quantity to add")
    session_key: str = strawberry.field(description="Anonymous session key", default="")

@strawberry.type
class AddToCartPayload:
    cart: Optional[CartType]
    errors: list[ErrorType]

@strawberry.type
class OrdersMutationExtension:
    @strawberry.mutation(description="Add an item to a cart. If cart doesn't exist, it will be created.")
    def add_to_cart(self, input: AddToCartInput) -> AddToCartPayload:
        try:
            cart = CartService.get_or_create_cart(session_key=input.session_key)
            CartService.add_item(cart=cart, product_id=input.product_id, quantity=input.quantity)
            return AddToCartPayload(cart=cart, errors=[])
        except Exception as e:
            return AddToCartPayload(cart=None, errors=[ErrorType(code="ADD_TO_CART_ERROR", message=str(e))])
