"""
Morpheus CMS — AI Assistant Plugin Manifest
The AI & Agent layer: Intent Engine, Memory, LLM Gateway, Semantic Search,
Autonomous Operator, Dynamic Assembly, A2A Commerce, Zero-Shot Catalog.
"""
from plugins.base import MorpheusPlugin
from core.hooks import MorpheusEvents


class AIAssistantPlugin(MorpheusPlugin):
    name = "ai_assistant"
    label = "AI Assistant & Agent Commerce"
    version = "1.0.0"
    description = (
        "Full AI-first commerce layer: intent resolution, agent memory, "
        "semantic search, autonomous store operator, A2A commerce, "
        "zero-shot catalog, and synthetic customer testing."
    )
    has_models = True
    requires = ["catalog", "orders", "customers"]

    def ready(self):
        # GraphQL extensions
        self.register_graphql_extension('plugins.installed.ai_assistant.graphql.queries')
        self.register_graphql_extension('plugins.installed.ai_assistant.graphql.mutations')
        
        # REST/Webhook/Manifest URLs
        self.register_urls('plugins.installed.ai_assistant.urls', prefix='api/')

        # React to store events
        self.register_hook(MorpheusEvents.ORDER_PLACED, self.on_order_placed, priority=80)
        self.register_hook(MorpheusEvents.PRODUCT_VIEWED, self.on_product_viewed, priority=80)
        self.register_hook(MorpheusEvents.CUSTOMER_REGISTERED, self.on_customer_registered, priority=80)
        self.register_hook(MorpheusEvents.SEARCH_PERFORMED, self.on_search_performed, priority=80)
        self.register_hook(MorpheusEvents.CART_ABANDONED, self.on_cart_abandoned, priority=80)
        self.register_hook(MorpheusEvents.PRODUCT_CREATED, self.on_product_created, priority=90)
        self.register_hook(MorpheusEvents.PRODUCT_UPDATED, self.on_product_updated, priority=90)

        # Price filter — AI can influence pricing
        self.register_hook(MorpheusEvents.PRODUCT_CALCULATE_PRICE, self.on_calculate_price, priority=50)

    def on_order_placed(self, order, **kwargs):
        """Update recommendation model after purchase."""
        from plugins.installed.ai_assistant.tasks import update_recommendations_after_order
        update_recommendations_after_order.delay(str(order.id))

    def on_product_viewed(self, product, customer=None, session_key=None, **kwargs):
        """Record product view for collaborative filtering."""
        from plugins.installed.ai_assistant.tasks import record_product_view
        record_product_view.delay(
            str(product.id),
            str(customer.id) if customer else None,
            session_key,
        )

    def on_customer_registered(self, customer, **kwargs):
        """Initialize memory store for new customer."""
        from plugins.installed.ai_assistant.tasks import initialize_customer_memory
        initialize_customer_memory.delay(str(customer.id))

    def on_search_performed(self, query, results_count=0, customer=None, **kwargs):
        """Log search for intent analysis and improving future results."""
        from plugins.installed.ai_assistant.tasks import log_search_event
        log_search_event.delay(query, results_count, str(customer.id) if customer else None)

    def on_cart_abandoned(self, cart, **kwargs):
        """Generate AI-personalized cart recovery message."""
        from plugins.installed.ai_assistant.tasks import generate_cart_recovery
        generate_cart_recovery.delay(str(cart.id))

    def on_product_created(self, product, **kwargs):
        """If product has no description, auto-generate one. Always (re)embed."""
        if not product.description:
            from plugins.installed.ai_assistant.tasks import generate_product_description
            generate_product_description.delay(str(product.id))
        self._enqueue_embedding(product)

    def on_product_updated(self, product, **kwargs):
        self._enqueue_embedding(product)

    def _enqueue_embedding(self, product) -> None:
        """Best-effort: schedule an embedding refresh; never raise from a hook."""
        try:
            from plugins.installed.ai_assistant.tasks import refresh_product_embedding
            refresh_product_embedding.delay(str(product.id))
        except Exception:  # noqa: BLE001 — task system may be down; degrade gracefully
            import logging
            logging.getLogger('morpheus.ai').warning(
                'Failed to enqueue embedding refresh for product %s', product.id,
            )

    def on_calculate_price(self, value, product=None, customer=None, **kwargs):
        """AI dynamic pricing hook — returns adjusted price if strategy active."""
        if not self.get_config_value('enable_dynamic_pricing', False):
            return value
        from plugins.installed.ai_assistant.services.pricing import DynamicPricingService
        return DynamicPricingService.calculate(value, product=product, customer=customer)

    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "ai_provider": {
                    "type": "string",
                    "enum": ["openai", "anthropic", "ollama"],
                    "default": "openai",
                    "title": "LLM Provider",
                },
                "enable_intent_engine": {"type": "boolean", "default": True},
                "enable_semantic_search": {"type": "boolean", "default": True},
                "enable_dynamic_pricing": {"type": "boolean", "default": False},
                "enable_zero_shot_catalog": {"type": "boolean", "default": True},
                "enable_autonomous_operator": {"type": "boolean", "default": False},
                "enable_synthetic_testing": {"type": "boolean", "default": False},
                "agent_purchase_requires_approval": {"type": "boolean", "default": True},
                "memory_confidence_decay_days": {"type": "integer", "default": 90},
            },
        }
