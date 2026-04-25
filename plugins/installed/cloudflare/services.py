"""Cloudflare API client + service helpers.

The HTTP layer is wrapped in a small `CloudflareClient` so tests can inject a
fake. Each public service function logs a `CacheInvalidation` audit row.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Sequence

from django.db import DatabaseError
from django.utils import timezone

logger = logging.getLogger('morpheus.cloudflare')


class CloudflareError(RuntimeError):
    """Raised when the Cloudflare API returns a non-success response."""


class CloudflareClient:
    """Thin Cloudflare API v4 client, scoped to a single account."""

    BASE_URL = 'https://api.cloudflare.com/client/v4'

    def __init__(self, *, api_token: str, session: Any | None = None) -> None:
        self._token = api_token
        self._session = session

    def _post(self, path: str, payload: dict | None) -> dict:
        if self._session is not None:
            return self._session.post(path, payload)
        import requests

        resp = requests.post(
            f'{self.BASE_URL}{path}',
            headers={
                'Authorization': f'Bearer {self._token}',
                'Content-Type': 'application/json',
            },
            json=payload or {},
            timeout=15,
        )
        body = resp.json() if resp.content else {}
        if not body.get('success', False):
            raise CloudflareError(
                f'Cloudflare API error ({resp.status_code}): {body.get("errors") or body}'
            )
        return body

    def purge_cache(
        self,
        zone_id: str,
        *,
        urls: Sequence[str] | None = None,
        tags: Sequence[str] | None = None,
        hosts: Sequence[str] | None = None,
        purge_everything: bool = False,
    ) -> dict:
        if purge_everything:
            payload = {'purge_everything': True}
        else:
            payload = {}
            if urls:
                payload['files'] = list(urls)
            if tags:
                payload['tags'] = list(tags)
            if hosts:
                payload['hosts'] = list(hosts)
            if not payload:
                raise ValueError('At least one of urls / tags / hosts must be provided.')
        return self._post(f'/zones/{zone_id}/purge_cache', payload)


def _client_for(zone) -> CloudflareClient:
    return CloudflareClient(api_token=zone.account.api_token)


def purge_urls(
    *,
    zone,
    urls: Iterable[str],
    triggered_by: str = '',
    client: CloudflareClient | None = None,
) -> 'CacheInvalidation':  # noqa: F821
    return _record_purge(
        zone=zone,
        scope='urls',
        targets=list(urls),
        triggered_by=triggered_by,
        client=client,
    )


def purge_tags(
    *,
    zone,
    tags: Iterable[str],
    triggered_by: str = '',
    client: CloudflareClient | None = None,
) -> 'CacheInvalidation':  # noqa: F821
    return _record_purge(
        zone=zone,
        scope='tags',
        targets=list(tags),
        triggered_by=triggered_by,
        client=client,
    )


def purge_everything(
    *,
    zone,
    triggered_by: str = '',
    client: CloudflareClient | None = None,
) -> 'CacheInvalidation':  # noqa: F821
    return _record_purge(
        zone=zone,
        scope='purge_everything',
        targets=[],
        triggered_by=triggered_by,
        client=client,
    )


def _record_purge(*, zone, scope, targets, triggered_by, client):
    from plugins.installed.cloudflare.models import CacheInvalidation

    inv = CacheInvalidation.objects.create(
        zone=zone, scope=scope, targets=targets, triggered_by=triggered_by[:120],
        status='pending',
    )

    cf = client or _client_for(zone)
    try:
        if scope == 'purge_everything':
            response = cf.purge_cache(zone.zone_id, purge_everything=True)
        elif scope == 'urls':
            response = cf.purge_cache(zone.zone_id, urls=targets)
        elif scope == 'tags':
            response = cf.purge_cache(zone.zone_id, tags=targets)
        elif scope == 'hosts':
            response = cf.purge_cache(zone.zone_id, hosts=targets)
        else:
            raise ValueError(f'Unknown scope: {scope}')
    except CloudflareError as e:
        inv.status = 'failed'
        inv.error_message = str(e)[:1000]
        inv.save(update_fields=['status', 'error_message'])
        logger.warning('cloudflare: purge failed for %s: %s', zone.domain, e)
        return inv
    except Exception as e:  # noqa: BLE001 — logged with traceback; never block hook chain
        inv.status = 'failed'
        inv.error_message = str(e)[:1000]
        inv.save(update_fields=['status', 'error_message'])
        logger.error('cloudflare: unexpected purge error for %s: %s', zone.domain, e, exc_info=True)
        return inv

    inv.status = 'succeeded'
    inv.response = response
    inv.save(update_fields=['status', 'response'])

    try:
        zone.last_purge_at = timezone.now()
        zone.save(update_fields=['last_purge_at'])
    except DatabaseError:
        pass

    return inv


def purge_for_product_update(product) -> list:
    """Auto-purge cache for any zone with `auto_purge_on_product_update=True`."""
    from plugins.installed.cloudflare.models import CloudflareZone

    invalidations = []
    qs = CloudflareZone.objects.filter(
        is_active=True, auto_purge_on_product_update=True,
    ).select_related('account')
    paths = [f'/p/{product.slug}', f'/products/{product.slug}']

    for zone in qs:
        urls = [f'https://{zone.domain}{path}' for path in paths]
        try:
            invalidations.append(
                purge_urls(zone=zone, urls=urls, triggered_by=f'product:{product.id}')
            )
        except Exception as e:  # noqa: BLE001 — never raise from a hook
            logger.warning('cloudflare: purge_for_product_update failed: %s', e)
    return invalidations
