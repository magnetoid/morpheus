"""Webhook delivery celery task."""
from __future__ import annotations

import logging

from django.utils import timezone

from morph.celery import app

logger = logging.getLogger('morpheus.webhooks_ui')


@app.task(name='webhooks_ui.deliver', acks_late=True, time_limit=20, soft_time_limit=10)
def deliver_webhook(delivery_id: str) -> None:
    from plugins.installed.webhooks_ui.models import WebhookDelivery
    from plugins.installed.webhooks_ui.services import build_signed_request_body, sign_payload

    try:
        d = WebhookDelivery.objects.select_related('endpoint').get(id=delivery_id)
    except WebhookDelivery.DoesNotExist:
        return
    if not d.endpoint.is_active:
        d.status = 'failed'
        d.error_message = 'endpoint inactive'
        d.save(update_fields=['status', 'error_message'])
        return

    d.status = 'delivering'
    d.attempts = (d.attempts or 0) + 1
    d.save(update_fields=['status', 'attempts'])

    body = build_signed_request_body(event_name=d.event_name, payload=d.payload)
    headers = {
        'Content-Type': 'application/json',
        'X-Morpheus-Event': d.event_name,
        'X-Morpheus-Signature': sign_payload(d.endpoint.secret or '', body),
    }
    try:
        import requests
        resp = requests.post(d.endpoint.url, data=body, headers=headers, timeout=10)
        d.response_status = resp.status_code
        d.response_body = (resp.text or '')[:5000]
        if 200 <= resp.status_code < 300:
            d.status = 'delivered'
            d.delivered_at = timezone.now()
        else:
            d.status = 'failed'
            d.error_message = f'HTTP {resp.status_code}'
    except Exception as e:  # noqa: BLE001
        d.status = 'failed'
        d.error_message = str(e)[:1000]
    d.save(update_fields=[
        'status', 'response_status', 'response_body',
        'error_message', 'delivered_at',
    ])
