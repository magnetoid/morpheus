from plugins.base import MorpheusPlugin

class MarketingPlugin(MorpheusPlugin):
    name = "marketing"
    label = "Marketing"
    version = "1.0.0"
    description = "Coupons, discount engine, email campaigns, and SEO redirects."
    has_models = True

    def ready(self):
        self.register_graphql_extension('plugins.installed.marketing.graphql.queries')
        self.register_graphql_extension('plugins.installed.marketing.graphql.mutations')
        self.register_hook('cart.abandoned', self.on_cart_abandoned, priority=30)

    def on_cart_abandoned(self, cart, **kwargs):
        from plugins.installed.marketing.tasks import trigger_cart_recovery_sequence
        trigger_cart_recovery_sequence.delay(str(cart.id))
