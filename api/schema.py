"""
Morpheus CMS — GraphQL Schema Assembly
Dynamically assembled from core types + all active plugin extensions.
"""
import strawberry
import logging

logger = logging.getLogger('morpheus.api')


@strawberry.type
class CoreQuery:
    @strawberry.field(description="Health check")
    def ping(self) -> str:
        return "pong"

    @strawberry.field(description="Morpheus CMS version")
    def version(self) -> str:
        return "1.0.0"

    @strawberry.field(description="List active plugins")
    def active_plugins(self) -> list[str]:
        from plugins.registry import plugin_registry
        return [p.name for p in plugin_registry.active_plugins()]


@strawberry.type
class CoreMutation:
    @strawberry.mutation
    def ping(self) -> str:
        return "pong"


def build_schema():
    """Build the root schema by assembling core + all plugin extensions."""
    from plugins.registry import plugin_registry
    import importlib

    query_bases = [CoreQuery]
    mutation_bases = [CoreMutation]

    for module_path in plugin_registry._graphql_extensions:
        try:
            mod = importlib.import_module(module_path)
            for attr_name in dir(mod):
                obj = getattr(mod, attr_name)
                if not isinstance(obj, type):
                    continue
                if attr_name.endswith('QueryExtension') and obj not in query_bases:
                    query_bases.append(obj)
                elif attr_name.endswith('MutationExtension') and obj not in mutation_bases:
                    mutation_bases.append(obj)
        except Exception as e:
            logger.error(f"Failed to load GraphQL extension {module_path}: {e}", exc_info=True)

    @strawberry.type
    class Query(*query_bases):
        pass

    @strawberry.type
    class Mutation(*mutation_bases):
        pass

    return strawberry.Schema(query=Query, mutation=Mutation)


import threading

_schema_lock = threading.Lock()
_cached_schema = None

def get_schema():
    global _cached_schema
    if _cached_schema is None:
        with _schema_lock:
            # Double-checked locking
            if _cached_schema is None:
                _cached_schema = build_schema()
    return _cached_schema
