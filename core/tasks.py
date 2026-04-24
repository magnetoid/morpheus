import json
import requests
import logging
from celery import shared_task

logger = logging.getLogger('morpheus.core.webhooks')

@shared_task(bind=True, max_retries=3)
def dispatch_webhook(self, url, secret, event_name, payload):
    """
    Asynchronously POSTs event data to an external Remote Plugin.
    Retries up to 3 times on failure.
    """
    headers = {
        'Content-Type': 'application/json',
        'X-Morpheus-Event': event_name,
        # In production, compute HMAC signature using 'secret' and payload 
        # to guarantee authenticity:
        # 'X-Morpheus-Signature': compute_hmac(payload, secret)
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        logger.info(f"Webhook delivered: {event_name} -> {url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Webhook failed: {event_name} -> {url}. Error: {e}")
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=2 ** self.request.retries)
