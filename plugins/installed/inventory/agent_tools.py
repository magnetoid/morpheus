"""Inventory tools the agent layer can call."""
from __future__ import annotations

from core.agents import ToolError, ToolResult, tool


@tool(
    name='inventory.low_stock_report',
    description='List products whose total stock is below `threshold`.',
    scopes=['inventory.read'],
    schema={
        'type': 'object',
        'properties': {
            'threshold': {'type': 'integer', 'minimum': 0, 'maximum': 1000, 'default': 5},
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 25},
        },
    },
)
def low_stock_report_tool(*, threshold: int = 5, limit: int = 25) -> ToolResult:
    from django.db.models import Sum, F
    from plugins.installed.inventory.models import StockLevel

    threshold = max(0, int(threshold or 5))
    limit = max(1, min(int(limit or 25), 100))
    rows = (
        StockLevel.objects
        .values(
            'variant__product__name',
            'variant__product__slug',
            'variant__sku',
        )
        .annotate(available=Sum(F('quantity') - F('reserved_quantity')))
        .filter(available__lte=threshold)
        .order_by('available')[:limit]
    )
    out = [
        {
            'product': r['variant__product__name'],
            'slug': r['variant__product__slug'],
            'variant_sku': r['variant__sku'],
            'available': r['available'] or 0,
        }
        for r in rows
    ]
    return ToolResult(output={'threshold': threshold, 'low_stock': out},
                      display=f'{len(out)} item(s) at or below {threshold}')


@tool(
    name='inventory.adjust_stock',
    description='Adjust on-hand stock for a variant in a warehouse. Positive `delta` adds stock; negative subtracts.',
    scopes=['inventory.write'],
    schema={
        'type': 'object',
        'properties': {
            'variant_sku': {'type': 'string'},
            'warehouse_code': {'type': 'string'},
            'delta': {'type': 'integer'},
            'reason': {'type': 'string'},
        },
        'required': ['variant_sku', 'warehouse_code', 'delta'],
    },
    requires_approval=True,
)
def adjust_stock_tool(
    *, variant_sku: str, warehouse_code: str, delta: int, reason: str = ''
) -> ToolResult:
    from django.db import transaction
    from plugins.installed.catalog.models import ProductVariant
    from plugins.installed.inventory.models import StockLevel, Warehouse

    try:
        variant = ProductVariant.objects.get(sku=variant_sku)
    except ProductVariant.DoesNotExist as e:
        raise ToolError(f'Unknown variant SKU: {variant_sku}') from e
    try:
        warehouse = Warehouse.objects.get(code=warehouse_code)
    except Warehouse.DoesNotExist as e:
        raise ToolError(f'Unknown warehouse code: {warehouse_code}') from e

    delta = int(delta)
    with transaction.atomic():
        level, _ = StockLevel.objects.select_for_update().get_or_create(
            variant=variant, warehouse=warehouse,
            defaults={'quantity': 0, 'reserved_quantity': 0},
        )
        new_qty = max(0, level.quantity + delta)
        level.quantity = new_qty
        level.save(update_fields=['quantity'])
    return ToolResult(
        output={'variant_sku': variant_sku, 'warehouse': warehouse_code,
                'new_quantity': new_qty, 'reason': reason},
        display=f'{variant_sku} @ {warehouse_code}: now {new_qty}',
    )
