"""Affiliate dashboard views (admin-only)."""
from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def affiliates_list(request):
    from plugins.installed.affiliates.models import Affiliate
    rows = list(Affiliate.objects.select_related('customer', 'program').order_by('-conversion_count')[:200])
    return render(request, 'affiliates/dashboard/affiliates_list.html', {
        'affiliates': rows, 'active_nav': 'growth',
    })


@staff_member_required
def payouts_list(request):
    from plugins.installed.affiliates.models import AffiliatePayout
    rows = list(AffiliatePayout.objects.select_related('affiliate__customer').order_by('-created_at')[:200])
    return render(request, 'affiliates/dashboard/payouts_list.html', {
        'payouts': rows, 'active_nav': 'growth',
    })
