from plugins.base import MorpheusPlugin

class InventoryPlugin(MorpheusPlugin):
    name = "inventory"
    label = "Inventory"
    version = "1.0.0"
    description = "Warehouses, stock levels, movements, and low-stock alerts."
    has_models = True
    requires = ["catalog"]

    def ready(self):
        self.register_graphql_extension('plugins.installed.inventory.graphql.queries')
        self.register_graphql_extension('plugins.installed.inventory.graphql.mutations')
        self.register_hook('order.placed', self.on_order_placed, priority=5)
        self.register_hook('order.cancelled', self.on_order_cancelled, priority=5)

    def on_order_placed(self, order, **kwargs):
        from plugins.installed.inventory.services import InventoryService
        InventoryService.reserve_for_order(order)

    def on_order_cancelled(self, order, **kwargs):
        from plugins.installed.inventory.services import InventoryService
        InventoryService.release_reservation(order)
