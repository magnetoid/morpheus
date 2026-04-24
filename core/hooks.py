"""
Morpheus CMS — Hook Registry
The event bus that connects all plugins without tight coupling.
"""
import logging
from collections import defaultdict
from typing import Any, Callable

logger = logging.getLogger('morpheus.hooks')


class HookRegistry:
    """
    Lightweight ordered event bus.

    Usage:
        # Register (in plugin.ready()):
        hook_registry.register('order.placed', handler, priority=10)

        # Fire (in service layer):
        hook_registry.fire('order.placed', order=order)

        # Filter (transform a value through a chain):
        price = hook_registry.filter('product.price', value=base_price, product=product)
    """

    def __init__(self):
        # { event_name: [ (priority, handler), ... ] }
        self._handlers: dict[str, list[tuple[int, Callable]]] = defaultdict(list)

    def register(self, event: str, handler: Callable, priority: int = 50) -> None:
        """Register a handler for an event. Lower priority = runs first."""
        self._handlers[event].append((priority, handler))
        self._handlers[event].sort(key=lambda x: x[0])
        logger.debug(f"Hook registered: {event} → {handler.__qualname__} (priority={priority})")

    def unregister(self, event: str, handler: Callable) -> None:
        """Remove a handler from an event."""
        self._handlers[event] = [
            (p, h) for p, h in self._handlers[event] if h != handler
        ]

    def fire(self, event: str, **kwargs: Any) -> list[Any]:
        """
        Fire an event. All registered handlers are called in priority order.
        Also dispatches asynchronous HTTP webhooks to Remote Plugins.
        Returns list of non-None return values from handlers.
        """
        results = []
        
        # 1. Dispatch Webhooks (Remote Plugins)
        # We wrap this in a try-except because apps aren't ready during initial module import
        try:
            from core.models import WebhookEndpoint
            from core.tasks import dispatch_webhook
            import json
            
            # Serialize payload (simplified for MVP)
            # In production, we need a robust JSON serializer that handles Model instances
            payload = {k: str(v) if hasattr(v, 'id') else v for k, v in kwargs.items() if isinstance(v, (str, int, float, bool, dict, list))}
            
            # We would normally filter WebhookEndpoints by 'events' JSONField containing 'event'
            endpoints = WebhookEndpoint.objects.filter(is_active=True)
            for endpoint in endpoints:
                if event in endpoint.events or '*' in endpoint.events:
                    dispatch_webhook.delay(endpoint.url, endpoint.secret, event, payload)
        except Exception as e:
            logger.debug(f"Webhook dispatch skipped or failed: {e}")

        # 2. Local Handlers (Native Plugins)
        for priority, handler in self._handlers.get(event, []):
            try:
                result = handler(**kwargs)
                if result is not None:
                    results.append(result)
            except Exception as e:
                logger.error(
                    f"Hook handler error: event={event} handler={handler.__qualname__} "
                    f"error={e}",
                    exc_info=True,
                )
        return results

    def filter(self, event: str, value: Any, **kwargs: Any) -> Any:
        """
        Filter an event — each handler receives the (potentially modified) value
        and returns a new value. Builds a transformation pipeline.
        """
        for priority, handler in self._handlers.get(event, []):
            try:
                result = handler(value=value, **kwargs)
                if result is not None:
                    value = result
            except Exception as e:
                logger.error(
                    f"Hook filter error: event={event} handler={handler.__qualname__} "
                    f"error={e}",
                    exc_info=True,
                )
        return value

    def has_handlers(self, event: str) -> bool:
        return bool(self._handlers.get(event))

    def list_handlers(self, event: str) -> list[str]:
        return [h.__qualname__ for _, h in self._handlers.get(event, [])]

    def clear(self, event: str | None = None) -> None:
        """Clear handlers. If event is None, clears all."""
        if event:
            self._handlers.pop(event, None)
        else:
            self._handlers.clear()


# Global singleton — import this everywhere
hook_registry = HookRegistry()


# ── Standard Morph events (for IDE autocompletion & discoverability) ──────────

class MorpheusEvents:
    """Catalogue of all built-in hook events."""

    # Orders
    ORDER_PLACED = 'order.placed'
    ORDER_CONFIRMED = 'order.confirmed'
    ORDER_PAID = 'order.paid'
    ORDER_CANCELLED = 'order.cancelled'
    ORDER_FULFILLED = 'order.fulfilled'

    # Payments
    PAYMENT_CAPTURED = 'payment.captured'
    PAYMENT_FAILED = 'payment.failed'
    PAYMENT_REFUNDED = 'payment.refunded'

    # Cart
    CART_CREATED = 'cart.created'
    CART_UPDATED = 'cart.updated'
    CART_ABANDONED = 'cart.abandoned'

    # Filters
    CART_CALCULATE_TOTAL = 'cart.calculate_total'   # filter
    PRODUCT_CALCULATE_PRICE = 'product.calculate_price'  # filter

    # Catalog
    PRODUCT_VIEWED = 'product.viewed'
    PRODUCT_CREATED = 'product.created'
    PRODUCT_UPDATED = 'product.updated'
    CATEGORY_UPDATED = 'category.updated'

    # Customers
    CUSTOMER_REGISTERED = 'customer.registered'
    CUSTOMER_LOGIN = 'customer.login'

    # Inventory
    PRODUCT_LOW_STOCK = 'product.low_stock'
    PRODUCT_OUT_OF_STOCK = 'product.out_of_stock'

    # Search
    SEARCH_PERFORMED = 'search.performed'

    # AI
    AI_DESCRIPTION_GENERATED = 'ai.description_generated'
    AI_RECOMMENDATION_REQUESTED = 'ai.recommendation_requested'
