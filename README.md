# Morpheus Engine

<div align="center">
  <p><strong>The first commerce platform built natively for AI agents.</strong></p>
  <p>Open-source. Plugin-native. Event-sourced. Production-grade.</p>
</div>

---

## Why Morpheus

Legacy commerce platforms (Shopify, WooCommerce, Magento, Spree) treat AI as
a third-party API consumer. Morpheus treats AI agents as the **primary
audience**: every feature, schema, and state transition is designed to be
machine-actionable first, human-pretty second.

Three things make it different from anything else open-source today:

1. **Agent-readable surface.** A `/graphql/agent/` endpoint, signed agent
   receipts, structured `agent_metadata` on every product, and a Python SDK
   so any LLM can browse, propose, and check out without scraping.
2. **Composability.** Everything beyond the bare engine is a plugin under
   `plugins/installed/`. 20 ship by default; the merchant can add more or
   disable any of them.
3. **Event-sourced + outbox-driven.** Every state change emits a hook +
   writes to a transactional outbox shipped to NATS JetStream. Replayable,
   auditable, fanout-friendly.

**Status:** 11 PRs landed, 20 plugins active, 98 / 98 tests green.

---

## Deploy in 60 seconds

### Coolify (recommended)

```
+ New Resource → Docker Compose
  Repo:         https://github.com/magnetoid/morpheus
  Compose file: docker-compose.yml          ← the default; no override needed
  Env vars:     paste from .env.coolify.example
  Domain:       bind your.domain.com to the `web` service
```

The default `docker-compose.yml` ships **web + worker + beat + postgres +
redis** wired through Coolify magic vars
(`SERVICE_FQDN_WEB`, `SERVICE_PASSWORD_POSTGRES`, `SERVICE_PASSWORD_REDIS`).
The `web` container's entrypoint waits for the DB, runs `migrate` +
`collectstatic`, then execs gunicorn.

→ Full guide: [`docs/deploy-coolify.md`](docs/deploy-coolify.md)
→ Behind Plesk Nginx: [`docs/deploy-plesk-nginx.md`](docs/deploy-plesk-nginx.md)

### Plain `docker compose`

```bash
git clone https://github.com/magnetoid/morpheus.git
cd morpheus
cp .env.example .env       # set SECRET_KEY, DATABASE_URL (Postgres), …
docker compose up -d
```

### Local dev (no Docker)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# DATABASE_URL must point at Postgres in non-test environments.
# (Tests run on SQLite-in-memory automatically.)
export DATABASE_URL=postgresql://user:pass@localhost/morpheus
export SECRET_KEY=dev-secret
export REDIS_URL=redis://localhost:6379/0

python manage.py migrate
python manage.py createsuperuser
python manage.py morph_seed_demo          # 25 demo books + 1 paid order
python manage.py runserver
celery -A morph worker -l info             # in another shell
celery -A morph beat -l info               # for observability rollups
```

→ For the full local stack (Supabase + observability):
`docker compose -f docker-compose.dev.yml up -d`

---

## What's inside

### Engine (the small core)

| Module | Role |
|---|---|
| [`core/`](core/) | hooks, models, tasks (HMAC-signed webhooks, NATS outbox), Celery, observability bootstrap, request_id, JSON logging, Sentry |
| [`api/`](api/) | GraphQL view (depth/alias guarded, masked errors), REST viewsets, agent-only endpoint, exception handler, rate limiter |
| [`plugins/`](plugins/) | plugin base class + registry with topological-sort activation; `morph_create_plugin` scaffolder |
| [`themes/`](themes/) | theme base + registry + ThemeLoader; `morph_create_theme` scaffolder |
| [`morph/`](morph/) | Django settings, ASGI/WSGI, Celery |

### First-party plugins (20)

| Plugin | What it does |
|---|---|
| [`catalog`](plugins/installed/catalog/) | Products, variants, categories, collections, attributes, vendors, reviews — `agent_metadata` on every Product |
| [`orders`](plugins/installed/orders/) | Cart → Order FSM, fulfillments, refunds, immutable `OrderEvent` log |
| [`customers`](plugins/installed/customers/) | Custom user + addresses |
| [`payments`](plugins/installed/payments/) | Stripe-first payment provider façade |
| [`inventory`](plugins/installed/inventory/) | Stock movements, low/out-of-stock hooks |
| [`marketing`](plugins/installed/marketing/) | Coupons, campaigns |
| [`analytics`](plugins/installed/analytics/) | Funnel events |
| [`ai_assistant`](plugins/installed/ai_assistant/) | Agent intent state machine, signed receipts, ProductEmbedding + semantic search, dynamic pricing, customer memory |
| [`ai_content`](plugins/installed/ai_content/) | Generative product copy |
| [`storefront`](plugins/installed/storefront/) | Public storefront views |
| [`admin_dashboard`](plugins/installed/admin_dashboard/) | Merchant admin (Shopify-style) |
| [`functions`](plugins/installed/functions/) | Sandboxed merchant-defined logic for cart totals, pricing, shipping, validation |
| [`importers`](plugins/installed/importers/) | Idempotent migrators: Shopify, WooCommerce, fixture loader |
| [`observability`](plugins/installed/observability/) | Per-merchant `MerchantMetric` rollups, `ErrorEvent` log, GraphQL series API |
| [`environments`](plugins/installed/environments/) | Dev/staging/prod with snapshots + promotion |
| [`affiliates`](plugins/installed/affiliates/) | Programs, links, attribution, payouts |
| [`marketplace`](plugins/installed/marketplace/) | Vendor onboarding, per-vendor order splitting, payouts |
| [`cloudflare`](plugins/installed/cloudflare/) | DNS, cache purge, WAF, R2 — auto-purge on `product.updated` |
| [`seo`](plugins/installed/seo/) | Per-object meta + JSON-LD, sitemap.xml, robots.txt, redirects, autofill |
| [`demo_data`](plugins/installed/demo_data/) | `manage.py morph_seed_demo` — bookstore fixtures |

### First-party theme

| Theme | Stack |
|---|---|
| [`dot_books`](themes/library/dot_books/) | Modern editorial bookstore — vanilla HTML5 + plain CSS variables, Fraunces + Inter, no Tailwind, no build step. ~2 KB CSS gzipped. **Active by default.** |

---

## Architecture cheat sheet

```
   Plesk Nginx (TLS)        Coolify Traefik           Morpheus
       ↓                          ↓                        ↓
  HTTPS in 443  →  HTTP :80  →  routes by Host  →  gunicorn (web)
                                                  ↓
                                          ┌───────┼────────┐
                                          ▼       ▼        ▼
                                       redis   postgres   celery worker + beat

  Hooks fired in `core/hooks.py`
  └─→ writes to OutboxEvent (transactional)
        └─→ Celery `process_outbox` publishes to NATS JetStream + remote webhooks
        └─→ HMAC-SHA256 signature on every webhook (X-Morpheus-Signature)
```

Key event flow: every domain transition (`order.placed`, `product.updated`,
`agent.intent.completed`, …) is **both** dispatched in-process to local
hooks **and** persisted to the outbox for at-least-once delivery to remote
subscribers.

---

## Production observability (built in)

- **Request ID:** every response carries `X-Request-ID`. Every log line
  includes it. Sentry events include it.
- **Structured logs:** JSON in production, pretty in DEBUG.
  See [`core/log_formatters.py`](core/log_formatters.py).
- **Sentry:** no-op until you set `SENTRY_DSN`. When set, scrubs auth
  tokens, cookies, password / secret / token / card from every event.
  See [`core/sentry.py`](core/sentry.py).
- **Errors are masked:** unhandled exceptions in DRF or GraphQL never leak
  stack traces. They get a stable error envelope with the request id and
  are written to the merchant `ErrorEvent` log.
- **Celery deadletter:** failed tasks land in `morpheus:deadletter:<task_id>`
  in Redis (7-day TTL).
- **MerchantMetric rollups:** hourly + daily Celery beat jobs roll
  `OutboxEvent` rows into time-series buckets. Query via
  `metricSeries(metric, granularity, hours)` GraphQL.

---

## Documentation

- [`SKILLS.md`](SKILLS.md) — **named procedures** for every common task
  (add a plugin, fix N+1, deploy to Coolify, …). Start here.
- [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md) — full plugin
  developer guide.
- [`docs/THEME_DEVELOPMENT.md`](docs/THEME_DEVELOPMENT.md) — full theme
  developer guide.
- [`docs/deploy-coolify.md`](docs/deploy-coolify.md) — Coolify deployment.
- [`docs/deploy-plesk-nginx.md`](docs/deploy-plesk-nginx.md) — Plesk Nginx
  → Coolify Traefik reverse proxy config.
- [`RULES.md`](RULES.md) — the platform's 13 immutable laws. Read before PR.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design, plugin lifecycle.
- [`AI_VISION.md`](AI_VISION.md) — strategic thesis.

---

## Scaffolders

```bash
python manage.py morph_create_plugin <name> [--with-models --with-graphql --with-urls --with-tasks]
python manage.py morph_create_theme  <name> [--from dot_books]
python manage.py morph_seed_demo    [--currency USD] [--fresh]
python manage.py morph_import shopify --shop=… --token=…
python manage.py morph_import woocommerce --base-url=… --consumer-key=… --consumer-secret=…
```

---

## Tech stack

- **Backend:** Python 3.12, Django 6
- **API:** Strawberry GraphQL + Django REST Framework
- **Database:** PostgreSQL — Supabase recommended; SQLite only for tests
- **Cache + queue:** Redis, Celery (`time_limit`/`soft_time_limit`/`acks_late`)
- **Event bus:** NATS JetStream (transactional outbox publisher)
- **Observability:** OpenTelemetry → OTLP collector → Prometheus / Grafana / Loki + Sentry
- **Containers:** multi-stage Dockerfile, non-root, gunicorn runtime, k8s manifests
- **SDK:** [`services/sdk_python`](services/sdk_python/) — `pip install -e services/sdk_python`

---

## Security defaults (changed from a vanilla Django template)

- `DEBUG = False` by default. `SECRET_KEY`, `ALLOWED_HOSTS`,
  `CORS_ALLOWED_ORIGINS`, `DATABASE_URL` are required in non-test envs.
- DRF default permission is `IsAuthenticated`; storefront catalog opts in
  to `AllowAny` explicitly.
- All webhooks ship with `X-Morpheus-Signature: sha256=<hmac>`.
- GraphQL has depth + alias caps (`GRAPHQL_MAX_QUERY_DEPTH`,
  `GRAPHQL_MAX_ALIASES`) and a `_MaskUnhandledErrors` extension.
- DRF + GraphQL exception handlers mask 5xx, surface `request_id`.
- `RateLimitMiddleware` wired on `/graphql` and `/v1/`.
- `IGNORE_EXCEPTIONS` on Redis cache — a Redis blip can't 500 the site.
- `SECURE_PROXY_SSL_HEADER` set to honor `X-Forwarded-Proto` from
  Plesk / Traefik / any TLS terminator.
- Sentry `before_send` scrubs auth tokens, cookies, and any
  password / secret / token / card key.

---

## Contributing

PRs welcome. The bar:

1. New behavior comes with tests. The whole suite is fast — keep it that way.
2. Don't add a top-level Django app for a new domain — make it a plugin
   ([Skill: add a new plugin](SKILLS.md#skill-add-a-new-plugin)).
3. Don't catch broad `Exception` without `exc_info=True` + a one-line reason.
4. Honor the security defaults in [`morph/settings.py`](morph/settings.py).
5. The change is reachable from a [skill in `SKILLS.md`](SKILLS.md) — add
   or update one in the same PR if it isn't.

---

## License

MIT. Build whatever you want with it.
