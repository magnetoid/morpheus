from plugins.installed.orders.models import Cart, CartItem, Order, OrderItem
from plugins.installed.catalog.models import Product, ProductVariant
from core.hooks import hook_registry
from typing import Optional, Dict

class CartService:
    @classmethod
    def get_or_create_cart(cls, session_key: str = "", customer=None) -> Cart:
        if customer:
            cart, _ = Cart.objects.get_or_create(customer=customer)
        else:
            cart, _ = Cart.objects.get_or_create(session_key=session_key, customer=None)
        return cart

    @classmethod
    def add_item(cls, cart: Cart, product_id: str, quantity: int = 1, variant_id: Optional[str] = None) -> CartItem:
        product = Product.objects.get(id=product_id)
        variant = ProductVariant.objects.get(id=variant_id) if variant_id else None
        
        # Determine unit price (variant price overrides product price)
        unit_price = variant.effective_price if variant else product.price
        
        item, created = CartItem.objects.get_or_create(
            cart=cart, 
            product=product,
            variant=variant,
            defaults={'quantity': quantity, 'unit_price': unit_price}
        )
        if not created:
            item.quantity += quantity
            item.save()
            
        return item

class OrderService:
    @classmethod
    def create_from_cart(cls, cart: Cart, email: str, shipping_address: Dict, billing_address: Dict) -> Order:
        order = Order.objects.create(
            customer=cart.customer,
            email=email,
            shipping_address=shipping_address,
            billing_address=billing_address,
            subtotal=cart.subtotal,
            total=cart.subtotal  # Simplified, skipping tax/shipping calc for now
        )
        
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                variant=cart_item.variant,
                product_name=cart_item.product.name,
                variant_name=cart_item.variant.name if cart_item.variant else "",
                sku=cart_item.variant.sku if cart_item.variant else cart_item.product.sku,
                quantity=cart_item.quantity,
                unit_price=cart_item.unit_price,
                total_price=cart_item.total_price
            )
            
        # Clear cart after successful order creation
        cart.items.all().delete()
        
        # Fire hook so inventory/plugins can react
        hook_registry.fire('order.placed', order=order)
        
        return order

    @classmethod
    def confirm_order(cls, order: Order):
        order.confirm()  # Uses django-fsm transition and Event Sourcing
        order.save()
        hook_registry.fire('order.confirmed', order=order)
