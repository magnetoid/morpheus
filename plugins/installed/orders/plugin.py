from plugins.base import MorpheusPlugin


class OrdersPlugin(MorpheusPlugin):
    name = "orders"
    label = "Orders"
    version = "1.0.0"
    description = "Cart, order lifecycle, fulfillment, and refunds."
    has_models = True
    requires = ["catalog", "customers"]

    def ready(self):
        self.register_graphql_extension('plugins.installed.orders.graphql.queries')
        self.register_graphql_extension('plugins.installed.orders.graphql.mutations')
        self.register_hook('payment.captured', self.on_payment_captured, priority=10)
        from plugins.installed.orders import signals  # noqa

    def on_payment_captured(self, payment, **kwargs):
        from plugins.installed.orders.services import OrderService
        OrderService.confirm_order(payment.order)
