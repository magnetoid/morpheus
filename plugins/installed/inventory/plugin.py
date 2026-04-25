from plugins.base import MorpheusPlugin


class InventoryPlugin(MorpheusPlugin):
    name = "inventory"
    label = "Inventory"
    version = "1.0.0"
    description = "Warehouses, stock levels, movements, low-stock alerts; atomic reservations."
    has_models = True
    requires = ["catalog"]

    def ready(self):
        self.register_graphql_extension('plugins.installed.inventory.graphql.queries')
        self.register_graphql_extension('plugins.installed.inventory.graphql.mutations')
        self.register_hook('order.placed',    self.on_order_placed,    priority=5)
        self.register_hook('order.paid',      self.on_order_paid,      priority=5)
        self.register_hook('order.cancelled', self.on_order_cancelled, priority=5)

    def on_order_placed(self, order, **kwargs):
        # Reserve stock when the order is created (before payment).
        from plugins.installed.inventory.services import InventoryService
        InventoryService.reserve_for_order(order)

    def on_order_paid(self, order, **kwargs):
        # Convert reservations into permanent decrements once payment lands.
        from plugins.installed.inventory.services import InventoryService
        InventoryService.commit_for_order(order)

    def on_order_cancelled(self, order, **kwargs):
        # Release reservations on cancel.
        from plugins.installed.inventory.services import InventoryService
        InventoryService.release_reservation(order)
