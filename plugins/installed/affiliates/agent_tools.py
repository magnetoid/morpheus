"""Affiliate agent tools."""
from __future__ import annotations

from decimal import Decimal

from djmoney.money import Money

from core.agents import ToolError, ToolResult, tool


@tool(
    name='affiliates.list_affiliates',
    description='List affiliates with their lifetime click/conversion/payout totals.',
    scopes=['affiliates.read'],
    schema={
        'type': 'object',
        'properties': {
            'limit': {'type': 'integer', 'minimum': 1, 'maximum': 100, 'default': 25},
        },
    },
)
def list_affiliates_tool(*, limit: int = 25) -> ToolResult:
    from plugins.installed.affiliates.models import Affiliate

    rows = list(Affiliate.objects.select_related('customer', 'program')[:max(1, min(int(limit or 25), 100))])
    return ToolResult(output={
        'affiliates': [
            {
                'code': a.code,
                'email': getattr(a.customer, 'email', '') if a.customer_id else '',
                'program': a.program.name if a.program_id else '',
                'click_count': a.click_count,
                'conversion_count': a.conversion_count,
                'lifetime_payout': str(getattr(a.lifetime_payout, 'amount', a.lifetime_payout or '')) if a.lifetime_payout else '',
                'is_active': a.is_active,
            }
            for a in rows
        ],
    })


@tool(
    name='affiliates.pending_payouts',
    description='List affiliate payouts in pending state.',
    scopes=['affiliates.read'],
    schema={'type': 'object', 'properties': {}},
)
def pending_payouts_tool() -> ToolResult:
    from plugins.installed.affiliates.models import AffiliatePayout
    rows = list(AffiliatePayout.objects.filter(status='pending').select_related('affiliate__customer')[:50])
    return ToolResult(output={
        'payouts': [
            {
                'id': str(p.id),
                'affiliate': p.affiliate.code,
                'amount': str(p.amount.amount),
                'currency': str(p.amount.currency),
                'method': p.method,
                'created_at': p.created_at.isoformat(),
            }
            for p in rows
        ],
    })


@tool(
    name='affiliates.mark_payout_paid',
    description='Mark a pending affiliate payout as paid (after external transfer).',
    scopes=['affiliates.write'],
    schema={
        'type': 'object',
        'properties': {
            'payout_id': {'type': 'string'},
            'external_reference': {'type': 'string', 'description': 'Bank/Stripe ref id'},
        },
        'required': ['payout_id'],
    },
    requires_approval=True,
)
def mark_payout_paid_tool(*, payout_id: str, external_reference: str = '') -> ToolResult:
    from plugins.installed.affiliates.models import AffiliatePayout
    from plugins.installed.affiliates.services import mark_payout_paid

    try:
        payout = AffiliatePayout.objects.get(id=payout_id)
    except AffiliatePayout.DoesNotExist as e:
        raise ToolError(f'Unknown payout: {payout_id}') from e
    mark_payout_paid(payout, external_reference=external_reference)
    return ToolResult(
        output={'payout_id': str(payout.id), 'status': payout.status},
        display=f'Marked payout {payout.id} paid',
    )


@tool(
    name='affiliates.create_affiliate',
    description='Create a new affiliate from a customer email.',
    scopes=['affiliates.write'],
    schema={
        'type': 'object',
        'properties': {
            'email': {'type': 'string'},
            'program_name': {'type': 'string', 'description': 'Optional program; defaults to first active program.'},
            'code': {'type': 'string', 'description': 'Optional custom code; auto-generated if omitted.'},
        },
        'required': ['email'],
    },
    requires_approval=True,
)
def create_affiliate_tool(*, email: str, program_name: str = '', code: str = '') -> ToolResult:
    import secrets
    from django.contrib.auth import get_user_model
    from plugins.installed.affiliates.models import Affiliate, AffiliateProgram

    User = get_user_model()
    customer = User.objects.filter(email__iexact=email).first()
    if not customer:
        raise ToolError(f'No customer with email {email}')
    program = (
        AffiliateProgram.objects.filter(name__iexact=program_name).first() if program_name
        else AffiliateProgram.objects.filter(is_active=True).order_by('-created_at').first()
    )
    if not program:
        raise ToolError('No active affiliate program. Create one in admin first.')
    affiliate, created = Affiliate.objects.get_or_create(
        customer=customer, program=program,
        defaults={'code': (code or secrets.token_urlsafe(6))[:32], 'is_active': True},
    )
    return ToolResult(
        output={'affiliate_id': str(affiliate.id), 'code': affiliate.code, 'created': created},
        display=f'{"Created" if created else "Found"} affiliate {affiliate.code}',
    )
