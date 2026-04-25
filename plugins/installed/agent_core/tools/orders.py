"""Order tools — read access for support + merchant agents."""
from __future__ import annotations

from core.agents import ToolError, ToolResult, tool


@tool(
    name='orders.list_recent',
    description='List the most recent orders. Limit is capped at 25.',
    scopes=['orders.read'],
    schema={
        'type': 'object',
        'properties': {
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 25, 'default': 10},
            'state': {'type': 'string', 'description': 'Filter by order state (e.g. pending, paid, shipped).'},
        },
    },
)
def list_recent_orders_tool(*, limit: int = 10, state: str = '') -> ToolResult:
    from plugins.installed.orders.models import Order

    limit = max(1, min(int(limit or 10), 25))
    qs = Order.objects.all().order_by('-created_at')
    if state:
        qs = qs.filter(state=state)
    rows = []
    for o in qs[:limit]:
        rows.append({
            'order_number': o.order_number,
            'state': o.state,
            'total': str(getattr(o.total, 'amount', '')),
            'currency': str(getattr(o.total, 'currency', '')),
            'created_at': o.created_at.isoformat(),
            'customer_email': getattr(o.customer, 'email', '') if o.customer_id else o.email,
        })
    return ToolResult(output={'orders': rows}, display=f'{len(rows)} order(s)')


@tool(
    name='orders.summary',
    description='Detailed summary of one order by order number.',
    scopes=['orders.read'],
    schema={
        'type': 'object',
        'properties': {'order_number': {'type': 'string'}},
        'required': ['order_number'],
    },
)
def summarise_order_tool(*, order_number: str) -> ToolResult:
    from plugins.installed.orders.models import Order

    try:
        order = Order.objects.prefetch_related('items').get(order_number=order_number)
    except Order.DoesNotExist as e:
        raise ToolError(f'Order not found: {order_number}') from e
    items = [
        {
            'product': i.product.name if i.product_id else i.product_name,
            'quantity': i.quantity,
            'unit_price': str(getattr(i.unit_price, 'amount', '')),
        }
        for i in order.items.all()
    ]
    return ToolResult(output={
        'order_number': order.order_number,
        'state': order.state,
        'total': str(getattr(order.total, 'amount', '')),
        'currency': str(getattr(order.total, 'currency', '')),
        'items': items,
        'created_at': order.created_at.isoformat(),
    })
