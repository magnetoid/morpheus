"""CMS dashboard pages."""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


def _safe_list(model_path, *, order_by='-updated_at', limit=200):
    try:
        from django.apps import apps
        app_label, model_name = model_path.split('.')
        return list(apps.get_model(app_label, model_name).objects.all().order_by(order_by)[:limit])
    except Exception:  # noqa: BLE001
        return []


@staff_member_required
def pages_list(request):
    rows = _safe_list('cms.Page')
    return render(request, 'cms/dashboard/pages.html', {'rows': rows, 'active_nav': 'cms'})


@staff_member_required
def blocks_list(request):
    rows = _safe_list('cms.Block', order_by='key')
    return render(request, 'cms/dashboard/blocks.html', {'rows': rows, 'active_nav': 'cms'})


@staff_member_required
def menus_list(request):
    rows = _safe_list('cms.Menu', order_by='key')
    return render(request, 'cms/dashboard/menus.html', {'rows': rows, 'active_nav': 'cms'})


@staff_member_required
def forms_list(request):
    rows = _safe_list('cms.Form', order_by='key')
    return render(request, 'cms/dashboard/forms.html', {'rows': rows, 'active_nav': 'cms'})
