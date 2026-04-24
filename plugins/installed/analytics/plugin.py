from plugins.base import MorpheusPlugin
from core.hooks import MorpheusEvents

class AnalyticsPlugin(MorpheusPlugin):
    name = "analytics"
    label = "Analytics"
    version = "1.0.0"
    description = "Event tracking, funnel analysis, and merchant dashboards."
    has_models = True

    def ready(self):
        self.register_graphql_extension('plugins.installed.analytics.graphql.queries')
        # Listen to all major events and log them
        for event in [
            MorpheusEvents.ORDER_PLACED, MorpheusEvents.PAYMENT_CAPTURED,
            MorpheusEvents.PRODUCT_VIEWED, MorpheusEvents.SEARCH_PERFORMED,
            MorpheusEvents.CUSTOMER_REGISTERED, MorpheusEvents.CART_ABANDONED,
        ]:
            self.register_hook(event, self.record_event, priority=99)

    def record_event(self, **kwargs):
        from plugins.installed.analytics.tasks import log_analytics_event
        # Fire and forget — never block the main flow
        log_analytics_event.delay(kwargs)
