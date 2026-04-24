"""
Internal GraphQL client — lets storefront views query the API
without going through HTTP. Never bypass this to use ORM directly.
"""
from strawberry.types import ExecutionResult


def internal_graphql(query: str, variables: dict | None = None, request=None) -> dict:
    """
    Execute a GraphQL query against the internal schema.
    Returns the data dict directly. Raises on errors.
    """
    from api.schema import get_schema
    schema = get_schema()
    context = {'request': request}
    result: ExecutionResult = schema.execute_sync(
        query,
        variable_values=variables or {},
        context_value=context,
    )
    if result.errors:
        import logging
        logging.getLogger('morpheus.api.client').error(
            f"Internal GraphQL errors: {result.errors}"
        )
    return result.data or {}
