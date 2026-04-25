# Morpheus Engine

<div align="center">
  <p><strong>The first commerce platform built natively for AI agents.</strong></p>
  <p>Open-source. Plugin-native. Event-sourced. Production-grade.</p>
</div>

---

## Why Morpheus

Legacy platforms (Shopify, WooCommerce, Magento, Spree, BigCommerce) treat AI as a third-party API consumer. Morpheus treats AI agents as the **primary audience**: every feature, schema, and state transition is designed to be machine-actionable first, human-pretty second.

The result is a stack that beats incumbents on three axes:

1. **Agent-readable surface.** A `/graphql/agent/` endpoint, signed agent receipts, structured `agent_metadata` on every product, and a Python SDK so any LLM can browse, propose, and check out without scraping.
2. **Composability.** Everything beyond the bare engine is a plugin under `plugins/installed/`. Catalog, orders, payments, AI, functions runtime, importers, observability, environments, affiliates, marketplace — they're all swappable.
3. **Event-sourced + outbox-driven.** Every state change emits a hook + writes to a transactional outbox shipped to NATS JetStream. Replayable, auditable, fanout-friendly.

---

## What's inside

### Engine (the small core)
| Module | Role |
|---|---|
| [`core/`](core/) | hooks, models, tasks (HMAC-signed webhooks, NATS outbox), Celery, observability bootstrap |
| [`api/`](api/) | GraphQL view (depth/alias guarded, `PermissionDenied` extension), REST viewsets, agent-only endpoint, rate limiter, type hints |
| [`plugins/`](plugins/) | plugin base class + registry with **topological-sort activation** |
| [`themes/`](themes/) | theme loader / context |
| [`morph/`](morph/) | Django settings, ASGI/WSGI, Celery |

### First-party plugins
| Plugin | What it does |
|---|---|
| [`catalog`](plugins/installed/catalog/) | Products, variants, categories, collections, attributes, vendors, reviews, **`agent_metadata` on every Product** |
| [`orders`](plugins/installed/orders/) | Cart → Order FSM, fulfillments, refunds, immutable `OrderEvent` log |
| [`customers`](plugins/installed/customers/) | Custom user + addresses |
| [`payments`](plugins/installed/payments/) | Stripe-first; provider façade for adding more |
| [`inventory`](plugins/installed/inventory/) | Stock movements, low/out-of-stock hooks |
| [`marketing`](plugins/installed/marketing/) | Coupons, campaigns |
| [`analytics`](plugins/installed/analytics/) | Funnel events |
| [`ai_assistant`](plugins/installed/ai_assistant/) | **Agent intent state machine, signed receipts, ProductEmbedding + semantic search, dynamic pricing, customer memory** |
| [`ai_content`](plugins/installed/ai_content/) | Generative product copy |
| [`storefront`](plugins/installed/storefront/) | Public storefront views |
| [`admin_dashboard`](plugins/installed/admin_dashboard/) | Merchant admin |
| [`functions`](plugins/installed/functions/) | **Sandboxed merchant-defined functions** for cart totals, product pricing, shipping, validation. Capability-grant model |
| [`importers`](plugins/installed/importers/) | **Idempotent migrators**: Shopify, WooCommerce. CLI: `manage.py morph_import shopify --shop=... --token=...` |
| [`observability`](plugins/installed/observability/) | Per-merchant `MerchantMetric` rollups (hourly + daily), `ErrorEvent` log, Celery beat schedules, GraphQL series API |
| [`environments`](plugins/installed/environments/) | **Dev / staging / production** with snapshots, promotion, rollback. Protected envs require `confirm=True` |
| [`affiliates`](plugins/installed/affiliates/) | Programs, links (`/r/<code>`), click tracking, last-click attribution, payouts |
| [`marketplace`](plugins/installed/marketplace/) | Vendor onboarding, **per-vendor order splitting** with commission, vendor payout accounts |

---

## Sprint status

| # | Theme | Status |
|---|---|---|
| 1 | Security + perf + ops baseline (HMAC webhooks, GraphQL auth guards, REST scoping, throttling, depth limits, indexes, gunicorn Dockerfile, CI) | ✅ |
| 2 | **Agent SDK alpha** + signed receipts + intent state machine | ✅ |
| 3 | **pgvector-aware semantic search** + auto-embed hooks + agent_metadata | ✅ |
| 4 | **Functions runtime** (sandboxed cart/price/shipping logic) | ✅ |
| 5 | **Importers plugin** (Shopify + WooCommerce + CLI) | ✅ |
| 6 | **Observability plugin** (per-merchant metric rollups + error log) | ✅ |
| 7 | **Environments plugin** (dev/staging/prod + snapshots + promotion) | ✅ |
| 8 | **Affiliates plugin** (links, attribution, payouts) | ✅ |
| 9 | **Marketplace plugin** (vendor onboarding, order splitting, payouts) | ✅ |

**Tests: 47/47 passing.** Lint via [pyproject.toml](pyproject.toml) (ruff, mypy, bandit, coverage).

---

## Tech stack

- **Backend:** Python 3.12, Django 6
- **API:** Strawberry GraphQL + Django REST Framework
- **Database:** PostgreSQL (Supabase-ready) with `pgvector` upgrade path; SQLite for dev
- **Cache + queue:** Redis, Celery (with `time_limit`/`soft_time_limit`/`acks_late`)
- **Event bus:** NATS JetStream (transactional outbox publisher)
- **Observability:** OpenTelemetry → OTLP collector → Prometheus / Grafana / Loki
- **Containers:** multi-stage Dockerfile with non-root gunicorn runtime, k8s manifests
- **SDK:** [`services/sdk_python`](services/sdk_python/) — `pip install -e services/sdk_python`

---

## Agent SDK quick taste

```python
from morph_sdk import MorphAgentClient

agent = MorphAgentClient(
    base_url="https://store.example.com",
    agent_token="<token>",
    signing_secret="<agent.signing_secret>",
)

products = agent.search_products("blender under 80 USD")

intent = agent.propose_intent(
    kind="checkout",
    summary="Buy the Vitamix Pro",
    payload={"product_id": products[0]["id"], "quantity": 1},
    estimated_amount=79.99,
)
# customer authorizes; platform completes the intent and signs the receipt

for done in agent.list_my_intents(state="completed"):
    receipt = agent.receipt_for(done)
    if receipt and receipt.verify():
        print("✅", receipt.intent_id, receipt.state)
```

---

## Functions runtime quick taste

```python
from plugins.installed.functions.runtime import execute

# Cart total: 10% off if subtotal > 100
result = execute(
    source="""
def run(input):
    sub = float(input["value"])
    return sub * 0.9 if sub > 100 else sub
""",
    input={"value": "120.00", "currency": "USD"},
    capabilities=["math", "money"],
    timeout_ms=200,
)
print(result.output)  # 108.0
```

The runtime refuses imports, dunder access, builtins like `open`/`exec`/`__import__`, and times out on runaway code.

---

## Quick start

```bash
git clone https://github.com/magnetoid/morpheus.git
cd morpheus
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env       # set SECRET_KEY, DATABASE_URL, REDIS_URL, …
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver

# in another shell:
celery -A morph worker -l info
celery -A morph beat -l info       # for observability rollups
```

### Production stack (default `docker-compose.yml`)

`docker-compose.yml` is the **production-ready** manifest: web + worker + beat + postgres + redis. Designed to be picked up zero-config by Coolify, Render, Railway, Dokku, fly.io, or plain `docker compose up -d`.

```bash
docker compose up -d
```

### Full dev stack

For the local *full* stack (Supabase + Redis + NATS + OTel collector + Prometheus + Grafana + Loki + Vector + ops-agent), use the dev compose:

```bash
docker compose -f docker-compose.dev.yml up -d
```

### Deploying to Coolify

The default compose file works out of the box. Full guide: [`docs/deploy-coolify.md`](docs/deploy-coolify.md).

```bash
# In Coolify: + New Resource → Docker Compose
#   Repo:         https://github.com/magnetoid/morpheus
#   Compose file: docker-compose.yml             ← default; nothing to set
#   Env vars:     paste from .env.coolify.example, set SECRET_KEY + Stripe + LLM keys
#   Domain:       bind your.domain.com to the `web` service
```

The compose ships **web + worker + beat + postgres + redis** wired through Coolify magic vars (`SERVICE_FQDN_WEB`, `SERVICE_PASSWORD_POSTGRES`, `SERVICE_PASSWORD_REDIS`) so credentials are auto-managed. The `web` container's entrypoint waits for the DB, runs `migrate` + `collectstatic`, then execs gunicorn.

### Importing an existing store

```bash
# Shopify
python manage.py morph_import shopify \
    --shop=my-shop --token=$SHOPIFY_TOKEN

# WooCommerce
python manage.py morph_import woocommerce \
    --base-url=https://shop.example.com \
    --consumer-key=$WC_KEY --consumer-secret=$WC_SECRET

# Or from a JSON fixture for reproducible imports / tests
python manage.py morph_import shopify --from-file=fixtures/shopify.json
```

---

## Security defaults (changed from the legacy template)

- `DEBUG=False` by default; `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` are required in prod
- DRF default permission is `IsAuthenticated`; storefront catalog opts in to `AllowAny`
- All webhooks ship with `X-Morpheus-Signature: sha256=<hmac>` — verifier in [`core/tasks.py`](core/tasks.py)
- GraphQL has depth/alias caps + `PermissionDenied` extension that emits `code: PERMISSION_DENIED`
- `RateLimitMiddleware` wired on `/graphql` and `/v1/`
- `IGNORE_EXCEPTIONS` on Redis cache — a Redis blip can't 500 the whole site
- Anti-pattern audit done: no broad `except Exception` left in the engine without `exc_info=True` + a documented reason

---

## Observability

| Surface | What you get |
|---|---|
| `/healthz` | Liveness |
| `/readyz` | DB + cache reachable |
| OTel | DjangoInstrumentor + RequestsInstrumentor + Psycopg2Instrumentor + RedisInstrumentor + CeleryInstrumentor |
| `MerchantMetric` | Per-channel hourly/daily rollups of `orders_placed`, `orders_paid`, `product_views`, `agent_intents_completed`, … |
| GraphQL `metricSeries(metric, granularity, hours)` | Time-series for the dashboard |

Beat schedule registered automatically by the [observability plugin](plugins/installed/observability/plugin.py).

---

## Documentation

- [`SKILLS.md`](SKILLS.md) — **the build & extend playbook**. Named, repeatable procedures for every common task (add a plugin, add a resolver, fix N+1, deploy to Coolify, …). Start here before writing code.
- [`RULES.md`](RULES.md) — the platform's 11 laws. Read before opening a PR.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design, plugin lifecycle, data flow.
- [`AI_VISION.md`](AI_VISION.md) — the agent-first thesis and roadmap.
- [`docs/deploy-coolify.md`](docs/deploy-coolify.md) — Coolify deployment.

---

## Contributing

PRs welcome. The bar:

1. New behavior comes with tests. The whole suite is fast — keep it that way.
2. Don't add a top-level Django app for a new domain — make it a plugin (see [Skill: add a new plugin](SKILLS.md#skill-add-a-new-plugin)).
3. Don't catch broad `Exception` without `exc_info=True` + a one-line comment explaining why.
4. Honor the security defaults in [`morph/settings.py`](morph/settings.py).
5. The change is reachable from a [skill in `SKILLS.md`](SKILLS.md) — add or update one in the same PR if it isn't.

---

## License

MIT. Build whatever you want with it.
