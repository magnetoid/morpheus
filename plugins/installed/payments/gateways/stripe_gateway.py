"""Stripe gateway — wraps the existing PaymentService into the new abstraction."""
from __future__ import annotations

import logging

from plugins.installed.payments.gateway import PaymentGateway

logger = logging.getLogger('morpheus.payments.stripe')


class StripeGateway(PaymentGateway):
    slug = 'stripe'
    label = 'Stripe'
    supports_refunds = True
    supports_webhooks = True

    def create_payment_intent(self, *, order, **kwargs) -> dict:
        from plugins.installed.payments.services.stripe import PaymentService
        return PaymentService.create_payment_intent(order)

    def refund(self, *, transaction, amount, **kwargs) -> dict:
        try:
            import stripe
            from django.conf import settings as dj_settings
            stripe.api_key = getattr(dj_settings, 'STRIPE_SECRET_KEY', '') or ''
            if not stripe.api_key:
                return {'success': False, 'error': 'STRIPE_SECRET_KEY missing'}
            charge_id = (transaction.metadata or {}).get('stripe_charge_id') if transaction else None
            if not charge_id:
                return {'success': False, 'error': 'no charge_id on transaction'}
            from decimal import Decimal
            stripe.Refund.create(
                charge=charge_id,
                amount=int(Decimal(amount.amount) * 100),
                idempotency_key=f'morph-refund-{transaction.id}',
            )
            return {'success': True}
        except Exception as e:  # noqa: BLE001
            logger.warning('stripe refund failed: %s', e)
            return {'success': False, 'error': str(e)[:200]}

    def webhook_verify(self, *, body: bytes, signature: str):
        try:
            from plugins.installed.payments.services.stripe import PaymentService
            event = PaymentService.verify_webhook(body, signature)
            return {'type': event.type, 'data': event.data.object} if event else None
        except Exception as e:  # noqa: BLE001
            logger.warning('stripe webhook verify failed: %s', e)
            return None
