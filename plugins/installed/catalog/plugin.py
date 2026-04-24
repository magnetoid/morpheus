from plugins.base import MorpheusPlugin


class CatalogPlugin(MorpheusPlugin):
    name = "catalog"
    label = "Product Catalog"
    version = "1.0.0"
    description = "Products, categories, collections, variants, attributes, and reviews."
    has_models = True

    def ready(self):
        self.register_graphql_extension('plugins.installed.catalog.graphql.queries')
        self.register_graphql_extension('plugins.installed.catalog.graphql.mutations')
        from plugins.installed.catalog import signals  # noqa - register signals
