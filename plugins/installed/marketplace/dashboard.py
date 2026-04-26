"""Marketplace dashboard pages (admin-only)."""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


def _safe_list(model_path, *, order_by='-created_at', limit=200):
    try:
        from django.apps import apps
        app_label, model_name = model_path.split('.')
        m = apps.get_model(app_label, model_name)
        return list(m.objects.all().order_by(order_by)[:limit])
    except Exception:  # noqa: BLE001
        return []


@staff_member_required
def vendors_list(request):
    rows = _safe_list('marketplace.Vendor')
    return render(request, 'marketplace/dashboard/list.html', {
        'rows': rows, 'title': 'Vendors',
        'columns': ['name', 'email', 'is_active', 'created_at'],
        'active_nav': 'marketplace',
    })


@staff_member_required
def vendor_orders(request):
    rows = _safe_list('marketplace.VendorOrder')
    return render(request, 'marketplace/dashboard/list.html', {
        'rows': rows, 'title': 'Vendor orders',
        'columns': ['vendor', 'order', 'state', 'subtotal'],
        'active_nav': 'marketplace',
    })


@staff_member_required
def payouts(request):
    rows = _safe_list('marketplace.VendorPayout')
    return render(request, 'marketplace/dashboard/list.html', {
        'rows': rows, 'title': 'Vendor payouts',
        'columns': ['vendor', 'amount', 'status', 'created_at'],
        'active_nav': 'marketplace',
    })
