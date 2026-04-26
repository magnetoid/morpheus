"""Dashboard views for draft orders."""
from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from plugins.installed.draft_orders import services
from plugins.installed.draft_orders.models import DraftOrder


@login_required
def index(request):
    drafts = DraftOrder.objects.select_related('customer', 'channel').order_by('-created_at')[:200]
    return render(request, 'draft_orders/index.html', {'drafts': drafts})


@login_required
def detail(request, number: str):
    draft = get_object_or_404(DraftOrder, number=number)
    return render(request, 'draft_orders/detail.html', {'draft': draft})


@login_required
def convert(request, number: str):
    draft = get_object_or_404(DraftOrder, number=number)
    if request.method == 'POST':
        services.recalc(draft)
        order = services.convert_to_order(draft)
        return redirect(f'/dashboard/orders/{order.order_number}/')
    return redirect(f'/dashboard/draft-orders/{draft.number}/')
