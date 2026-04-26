<div align="center">

# Morpheus

### The first commerce platform built natively for AI agents.

**Open source · Plugin-native · Event-sourced · Production-grade**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Live demo](https://img.shields.io/badge/live-dotbooks.store-ff5722.svg)](https://dotbooks.store)
[![Plugins](https://img.shields.io/badge/plugins-33%20active-blue.svg)](#whats-inside)
[![Status](https://img.shields.io/badge/status-v0.1.0%20%2B%20Phase%205-brightgreen.svg)](#changelog)

[Quick start](#quick-start) · [The mental model](#the-mental-model) · [What's inside](#whats-inside) · [Agent layer](#the-agent-layer) · [Saleor parity](#saleor-parity) · [Docs](#documentation)

</div>

---

## Why Morpheus exists

Every commerce platform built before 2024 — Shopify, WooCommerce, Magento, Spree, Saleor — treats AI as a *third-party API consumer*. You bolt OpenAI onto a checkbox in settings, hope the prompt is good, and pay an integration tax forever.

**Morpheus inverts that.** AI agents are the *primary audience*. Every model, hook, dashboard, and state transition is designed to be machine-actionable first and human-pretty second. The Assistant is not a chatbot tab — it's a hard-coded operator in `core/` that survives plugin failure, has system-level scopes, and can delegate to specialised agents that other plugins contribute.

What you get:

| Pillar | What it means in practice |
|---|---|
| **Hard-coded Assistant in core** | A single Morpheus Assistant lives in [`core/assistant/`](core/assistant/) — never a plugin. System tools (filesystem, DB introspection, logs, plugin status, server info, delegate). JSONL fallback persistence so the chat works even when the DB is unreachable. |
| **Kernel agent layer** | [`core/agents/`](core/agents/) is a peer of `core/hooks` and `plugins/`. Real LLM tool-use loop, provider abstraction (OpenAI / Anthropic / Ollama / Mock), versioned prompts, capability scopes, lossless trace, **Skills** (reusable tool bundles), background scheduling. |
| **Plugin-native everything** | 33 plugins ship enabled. Each contributes any of: storefront blocks, dashboard pages, settings panels, hooks, agents, agent tools, skills, URLs, GraphQL extensions, beat tasks. Disable any of them, the engine still boots. |
| **Event-sourced + outbox** | Every state change emits a hook *and* writes to a transactional outbox shipped to NATS JetStream. Replayable, auditable, fanout-friendly. HMAC-SHA256 on every outbound webhook. |
| **Agent-readable commerce surface** | A `/graphql/agent/` endpoint, signed agent receipts, structured `agent_metadata` on every product, a Python SDK so any LLM can browse, propose, and check out without scraping. |

Live deployment: **https://dotbooks.store** · v0.1.0 + Phase 5 · 50+ merged PRs · 33 plugins · 5 built-in agents · 1 hard-coded Assistant.

---

## Quick start

### Deploy to Coolify (the recommended path)

```text
+ New Resource → Docker Compose
  Repo:         https://github.com/magnetoid/morpheus
  Compose file: docker-compose.yml          ← default; no override needed
  Env vars:     paste from .env.coolify.example
  Domain:       bind your.domain.com to the `web` service
```

The default `docker-compose.yml` ships **web + worker + beat + postgres + redis** wired through Coolify magic vars (`SERVICE_FQDN_WEB`, `SERVICE_PASSWORD_POSTGRES`, `SERVICE_PASSWORD_REDIS`). The web container's entrypoint waits for the DB, runs `migrate` + `collectstatic`, then execs gunicorn.

Full guide: [`docs/deploy-coolify.md`](docs/deploy-coolify.md) · Behind Plesk Nginx: [`docs/deploy-plesk-nginx.md`](docs/deploy-plesk-nginx.md)

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

export DATABASE_URL=postgresql://user:pass@localhost/morpheus
export SECRET_KEY=dev-secret
export REDIS_URL=redis://localhost:6379/0

python manage.py migrate
python manage.py createsuperuser
python manage.py morph_seed_demo          # 25 demo books + 1 paid order
python manage.py runserver

celery -A morph worker -l info             # in another shell
celery -A morph beat -l info               # for observability rollups + agent scheduler
```

For the full stack with observability: `docker compose -f docker-compose.dev.yml up -d`

---

## The mental model

There are **three layers** and **two registries**. Internalise this and the rest of the codebase reads itself.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                LAYER 1 — CORE                                │
│  Tiny, almost everything else can be ripped out and the engine still boots.  │
│                                                                              │
│  core/                hooks · models · tasks · settings · request_id · logs  │
│  core/assistant/      ★ HARD-CODED MORPHEUS ASSISTANT (always reachable)     │
│  core/agents/         ★ Agent kernel (MorpheusAgent · Tool · Skill · LLM)    │
│  core/audit/          ★ Tamper-evident security log (`record(...)`)          │
│  core/i18n/           ★ Translation kernel (generic-FK Translation rows)     │
│  core/embeddings.py   ★ Embedding provider abstraction                       │
│  core/utils/          ★ safe_db decorator · sliding-window rate limiter      │
│  core/management/     ★ morph_backup (pg_dump + media tar)                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                          ┌──────────┼──────────┐
                          ▼          ▼          ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              LAYER 2 — PLUGINS                                │
│           33 enabled by default. Each is a self-contained Python package.    │
│                                                                              │
│  COMMERCE          AGENT             GROWTH            INFRA / OPS           │
│  catalog           agent_core        crm               cloudflare            │
│  orders            ai_assistant      affiliates        observability         │
│  customers         ai_content        marketplace       environments          │
│  payments          functions         marketing         importers             │
│  inventory                           wishlist          seo                   │
│  cms               ★ Skills are      gift_cards        webhooks_ui           │
│  tax                  reusable        b2b              demo_data             │
│  shipping             tool bundles    subscriptions    advanced_ecommerce    │
│  promotions ★         any agent       loyalty_points   admin_dashboard       │
│  draft_orders ★       opts into.      reviews          rbac ★                │
│  storefront                                                                   │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
                                     ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              LAYER 3 — THEMES                                 │
│       Plugins ship features. Themes ship presentation. They never mix.       │
│                                                                              │
│  themes/library/dot_books/   ← active by default; modern editorial           │
│                                                                              │
│  Plugins contribute via {% storefront_blocks "slot" %} into theme slots.     │
│  The theme owns layout + CSS + which slots exist — that's the boundary.      │
└──────────────────────────────────────────────────────────────────────────────┘

The two registries that wire it all together:

  PluginRegistry        — discovers, topologically sorts, activates.
                          Collects each plugin's contributions:
                          • storefront blocks  • dashboard pages  • settings panels
                          • agents · agent tools · skills · URLs · GraphQL extensions

  AgentRegistry         — knows every Tool and every Agent the platform exposes.
                          Skills resolve into Tool bundles at agent invocation time.
```

★ = added during the latest wave (Phase 5).

### Two non-obvious rules

1. **The Assistant is not a plugin.** Lives in `core/`. Survives plugin failure. Has its own URL (`/admin/assistant/`) mounted *before* the Django admin. JSONL fallback persistence so the chat keeps working when the DB is down.
2. **Operational pages live in the main sidebar; only persistent configuration lives in Settings.** Promotions, draft orders, demo-data generators — those are *operational pages* and surface under main-menu sections (Marketing / Sales / Catalog). Settings panels are reserved for things you set once: API keys, provider choice, on/off toggles. This is enforced in plugin code (`contribute_dashboard_pages` vs. `contribute_settings_panel`).

---

## What's inside

### Engine modules (`core/` — the small fixed surface)

| Module | Role |
|---|---|
| [`core/`](core/) | hooks, models, Celery, observability bootstrap, request_id, JSON logging, Sentry, channels, exchange rates |
| [`core/assistant/`](core/assistant/) | **Hard-coded Morpheus Assistant** — runtime, providers, system tools (filesystem/DB/logs/plugins/server/delegate), JSONL-fallback persistence |
| [`core/agents/`](core/agents/) | Agent kernel — `MorpheusAgent`, `Tool`, **`Skill`**, `AgentRuntime`, `LLMProvider`, prompts registry, scopes, trace, policies |
| [`core/audit/`](core/audit/) | **Tamper-evident audit log** — `core.audit.record(event_type, actor, target, metadata)` |
| [`core/i18n/`](core/i18n/) | **Translation kernel** — generic-FK `Translation` rows, `{{ obj\|trans:"field" }}`, agent tools |
| [`core/embeddings.py`](core/embeddings.py) | **Embedding provider abstraction** — promoted from `ai_assistant`; deterministic-hash fallback |
| [`core/utils/`](core/utils/) | `safe_db` decorator · sliding-window `rate_limit` |
| [`core/management/commands/`](core/management/commands/) | `morph_backup` — pg_dump + media tar with retention |
| [`api/`](api/) | GraphQL view (depth/alias guarded, masked errors), REST viewsets, agent-only endpoint, exception handler, rate limiter |
| [`plugins/`](plugins/) | plugin base class + registry with topological-sort activation; `morph_create_plugin` scaffolder |
| [`themes/`](themes/) | theme base + registry + ThemeLoader; `morph_create_theme` scaffolder |
| [`morph/`](morph/) | Django settings, ASGI/WSGI, Celery |

### First-party plugins (33 active)

| Plugin | What it does |
|---|---|
| [`catalog`](plugins/installed/catalog/) | Products, variants, categories, collections, attributes, vendors, reviews — `agent_metadata` on every Product |
| [`orders`](plugins/installed/orders/) | Cart → Order FSM, fulfillments, refunds, immutable `OrderEvent` log |
| [`customers`](plugins/installed/customers/) | Custom user + addresses |
| [`payments`](plugins/installed/payments/) | **`PaymentGateway` ABC + `GatewayRegistry`**. Stripe + Manual adapters. Drop-in slot for PayPal / Payoneer / Adyen |
| [`inventory`](plugins/installed/inventory/) | Stock movements, low/back-in-stock hooks, **`allocator.plan_allocation()` — multi-warehouse stock splits** |
| [`promotions`](plugins/installed/promotions/) ★ | **Rule-based promotion engine**. JSON predicates × actions (% off, fixed off, free shipping, gift). Channel-scoped, time-bounded, audit-logged |
| [`draft_orders`](plugins/installed/draft_orders/) ★ | **Quote / invoice flow**. Build a priced cart, share with customer, convert to a real Order on payment |
| [`marketing`](plugins/installed/marketing/) | Coupons, email campaigns, redirects |
| [`analytics`](plugins/installed/analytics/) | Sessions, events, daily metric rollups, funnel definitions |
| [`ai_assistant`](plugins/installed/ai_assistant/) | **AI Signals layer** — embeddings, semantic search, recommendations, dynamic pricing. (Agent runtime now lives in `core.agents` + `agent_core`) |
| [`ai_content`](plugins/installed/ai_content/) | Generative product copy |
| [`storefront`](plugins/installed/storefront/) | Public storefront views, customer account v2 (orders, addresses, returns, profile) |
| [`admin_dashboard`](plugins/installed/admin_dashboard/) | Merchant admin (Shopify-style sidebar with collapsible sections + settings mode + top-right user menu) |
| [`functions`](plugins/installed/functions/) | Sandboxed merchant-defined logic for cart totals, pricing, shipping, validation |
| [`importers`](plugins/installed/importers/) | Idempotent migrators: Shopify, WooCommerce, fixture loader. **Bulk CSV products import + export** |
| [`observability`](plugins/installed/observability/) | Per-merchant `MerchantMetric` rollups, `ErrorEvent` log, GraphQL series API |
| [`environments`](plugins/installed/environments/) | Dev/staging/prod with snapshots + promotion |
| [`affiliates`](plugins/installed/affiliates/) | Programs, links, attribution, payouts |
| [`marketplace`](plugins/installed/marketplace/) | Vendor onboarding, per-vendor order splitting, payouts |
| [`cloudflare`](plugins/installed/cloudflare/) | DNS, cache purge, WAF, R2 — auto-purge on `product.updated` |
| [`seo`](plugins/installed/seo/) | Per-object meta, full JSON-LD (Product, Org, BreadcrumbList, WebSite, Article, FAQ), sitemap.xml, robots.txt, redirects, `/llms.txt` for LLM crawlers |
| [`demo_data`](plugins/installed/demo_data/) | `manage.py morph_seed_demo` + theme-aware on-demand random product generator |
| [`advanced_ecommerce`](plugins/installed/advanced_ecommerce/) | Recently viewed, free-shipping progress, low-stock badge — reference plugin for contribution surfaces |
| [`agent_core`](plugins/installed/agent_core/) | **Persistence + GraphQL + dashboard for the agent kernel.** Built-in agents (Concierge, Merchant Ops, Pricing, Content Writer). **Background agents lifecycle. Observability dashboard** |
| [`crm`](plugins/installed/crm/) | Leads, accounts, deals, interactions timeline, follow-up tasks; ships the Account Manager agent |
| [`tax`](plugins/installed/tax/) | Regions, categorised rates (US sales tax / EU VAT / OSS); cart-total hook |
| [`shipping`](plugins/installed/shipping/) | Zones + rates (flat / weight / order-total tier / free-over / Shippo / EasyPost slots) |
| [`wishlist`](plugins/installed/wishlist/) | Customer + guest wishlists with shareable links |
| [`webhooks_ui`](plugins/installed/webhooks_ui/) | Endpoint CRUD + delivery log with retry/replay; HMAC-SHA256 signed |
| [`gift_cards`](plugins/installed/gift_cards/) | Issue / redeem / balance, append-only ledger |
| [`b2b`](plugins/installed/b2b/) | Quotes + per-account price lists + Net 15/30/45/60/90 |
| [`subscriptions`](plugins/installed/subscriptions/) | Plan + Subscription + invoice; Stripe Billing adapter slot |
| [`cms`](plugins/installed/cms/) | Pages (state machine), Blocks, Menus, Forms (form submissions bridge into CRM as Lead+Interaction) |
| [`rbac`](plugins/installed/rbac/) ★ | **Named roles + capabilities** — 6 system role templates (admin, marketing_manager, inventory_manager, support_agent, analyst, content_editor). `has_capability(user, cap, channel=None)`. Audit-logged grants/revokes |

★ = shipped during Phase 5.

### First-party theme

| Theme | Stack |
|---|---|
| [`dot_books`](themes/library/dot_books/) | Modern editorial bookstore — vanilla HTML5 + plain CSS variables, Fraunces + Inter, no Tailwind, no build step. ~2 KB CSS gzipped. **Active by default.** |

---

## The agent layer

This is what makes Morpheus different from every other open-source commerce platform.

### 1. The Assistant (always-on, hard-coded)

[`core/assistant/`](core/assistant/) defines a single `Assistant` class. Mounted at `/admin/assistant/` *before* the Django admin in [`morph/urls.py`](morph/urls.py) so it remains reachable even if every plugin import explodes.

What it can do, out of the box:

- Read files (`filesystem.read`)
- Inspect the database (`database.list_tables`, `database.describe`, `database.query`)
- Search logs (`logs.search`)
- List + introspect plugins (`plugins.list`, `plugins.describe`)
- Server info (`system.info`, `system.git_log`)
- Delegate to any registered agent (`delegate.invoke_agent`)

When the database is unreachable, the Assistant's chat history persists to JSONL files at `/tmp/morpheus-assistant/` so you can still talk to it. A floating chat widget is included on every admin page via the `{% morph_ask %}` template tag, with auto-context derived from `request.path`.

### 2. The Kernel (`core/agents/`)

A peer of `core/hooks` and `plugins/`. The substrate every agent (built-in or plugin-contributed) builds on:

```python
from core.agents import (
    MorpheusAgent, Tool, ToolResult, tool, Skill,
    AgentRuntime, LLMProvider, get_llm_provider,
    AgentTrace, agent_registry, skill_registry,
)
```

Concepts:

- **`MorpheusAgent`** — base class. Declare `name`, `label`, `audience` (`storefront` / `merchant` / `system` / `any`), `scopes`, `prompt_name`, `provider`, `model`, `default_tools`, **`uses_skills`**.
- **`Tool`** — a single capability with a JSON Schema, scope list, and an optional `requires_approval` gate. Decorated with `@tool(...)`.
- **`Skill`** ★ — a labeled bundle of tools + an optional system-prompt prelude. Plugins ship skills via `contribute_skills()`. Agents opt in via `uses_skills = ('storefront_concierge',)`. Replaces the "duplicate the tool list on every agent" pattern.
- **`AgentRuntime`** — real LLM tool-use loop. Streams `TraceStep`s in order: `system → user → tool_call → tool_result → ... → final`.
- **`LLMProvider`** — abstraction over OpenAI / Anthropic / Ollama / Mock. Selected by `settings.MORPHEUS_LLM_PROVIDER`.
- **Prompts** — versioned, looked up by name in `prompt_registry`.
- **Policies** — `enforce_policy(...)` raises `ScopeDenied` / `BudgetExceeded` before the agent can call a tool it shouldn't.
- **Trace** — every run captures every step. Persisted to `AgentRun` + `AgentStep` rows by `agent_core` so you get a lossless audit trail in the dashboard.

### 3. Built-in agents (shipped by `agent_core` + `crm`)

| Agent | Audience | What it does |
|---|---|---|
| **Concierge** | storefront | Helps shoppers — searches catalog, recommends, answers product questions |
| **Merchant Ops** | merchant | Admin assistant — runs reports, drafts emails, queries the DB through tools |
| **Pricing** | system | Reviews and adjusts prices via the `product.calculate_price` hook |
| **Content Writer** | merchant | Generates SEO copy, product descriptions, blog posts |
| **Account Manager** | merchant | (CRM) Surfaces deal stage changes, follow-up tasks, lead-to-customer journeys |

### 4. Background agents ★

[`/dashboard/agents/background/`](https://dotbooks.store/dashboard/agents/background/)

Schedule any registered agent to run autonomously on a fixed interval. Backed by `BackgroundAgent` model + Celery beat (fires every minute). After `max_failures_before_pause` consecutive failures (default 5) an agent auto-pauses so a broken job can't burn through tokens. Reschedules **before** fire so concurrent beats can't double-run.

### 5. Observability dashboard ★

[`/dashboard/agents/observability/`](https://dotbooks.store/dashboard/agents/observability/)

Per-agent runs / tokens / tool calls / avg duration over a configurable window (1 / 7 / 30 / 90 days), state breakdown, top tools, recent failures linking to run detail.

### 6. Per-user rate limit ★

`core.utils.rate_limit` — sliding-window limiter on Django cache. Wired into the agent invoke endpoint at **20 req/min per authenticated user or IP**. First defense against accidental token spend.

---

## Saleor parity

A live tracker of how Morpheus compares to Saleor, the previous open-source benchmark.

| Capability | Saleor | Morpheus |
|---|---|---|
| Plugin architecture | ✅ | ✅ (`plugins/installed/`) |
| GraphQL API | ✅ | ✅ (Strawberry) |
| REST API | ❌ | ✅ (DRF) |
| Multi-channel + per-channel pricing | ✅ | ✅ (`core.StoreChannel` + `ProductChannelListing`) |
| Multi-currency | ✅ | ✅ (`core.ExchangeRate` + display currency context) |
| Translations | ✅ | ✅ (`core.i18n` — generic-FK `Translation` rows) |
| Payment gateway abstraction | ✅ | ✅ (`PaymentGateway` ABC + `GatewayRegistry`) |
| Promotion engine (rule-based) | ✅ | ✅ (`promotions` plugin — predicates × actions) |
| Draft orders / quotes | ✅ | ✅ (`draft_orders` plugin) |
| Multi-warehouse stock allocation | ✅ | ✅ (`inventory.allocator.plan_allocation`) |
| RBAC / permissions | ✅ | ✅ (`rbac` plugin — capabilities) |
| Webhooks (signed, retry/replay) | ✅ | ✅ (HMAC-SHA256, `webhooks_ui` plugin) |
| Audit log | ✅ | ✅ (`core.audit` — tamper-evident) |
| Bulk CSV import / export | partial | ✅ (`importers/adapters/csv_products`) |
| Backups (pg_dump + media) | manual | ✅ (`manage.py morph_backup`) |
| **Hard-coded Assistant** | ❌ | ✅ |
| **Kernel agent layer (with tool-use loop, scopes, trace)** | ❌ | ✅ |
| **Background agents (scheduled autonomous runs)** | ❌ | ✅ |
| **Skills (reusable tool bundles)** | ❌ | ✅ |
| **Agent observability dashboard** | ❌ | ✅ |
| **Agent-readable commerce surface (`/llms.txt`, agent receipts, agent GraphQL)** | ❌ | ✅ |

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

Every domain transition (`order.placed`, `product.updated`, `agent.intent.completed`, …) is **both** dispatched in-process to local hooks **and** persisted to the outbox for at-least-once delivery to remote subscribers.

---

## Production observability (built in)

- **Request ID** — every response carries `X-Request-ID`. Every log line includes it. Sentry events include it.
- **Structured logs** — JSON in production, pretty in DEBUG. See [`core/log_formatters.py`](core/log_formatters.py).
- **Sentry** — no-op until you set `SENTRY_DSN`. When set, scrubs auth tokens, cookies, password / secret / token / card from every event. See [`core/sentry.py`](core/sentry.py).
- **Errors are masked** — unhandled exceptions in DRF or GraphQL never leak stack traces. They get a stable error envelope with the request id and are written to the merchant `ErrorEvent` log.
- **Audit log** ★ — `core.audit.record(...)` writes a tamper-evident `AuditEvent` row for security-grade events (RBAC grants, agent approvals, gateway changes).
- **Celery deadletter** — failed tasks land in `morpheus:deadletter:<task_id>` in Redis (7-day TTL).
- **MerchantMetric rollups** — hourly + daily Celery beat jobs roll `OutboxEvent` rows into time-series buckets. Query via `metricSeries(metric, granularity, hours)` GraphQL.
- **Agent observability** ★ — per-agent runs / tokens / tool calls / avg duration at `/dashboard/agents/observability/`.

---

## Scaffolders

```bash
python manage.py morph_create_plugin <name> [--with-models --with-graphql --with-urls --with-tasks]
python manage.py morph_create_theme  <name> [--from dot_books]
python manage.py morph_seed_demo            [--currency USD] [--fresh]
python manage.py morph_import shopify       --shop=… --token=…
python manage.py morph_import woocommerce   --base-url=… --consumer-key=… --consumer-secret=…
python manage.py morph_backup               [--dest /var/backups/morpheus] [--keep 7]    # ★
```

---

## Tech stack

- **Backend:** Python 3.12, Django 6
- **API:** Strawberry GraphQL + Django REST Framework
- **Database:** PostgreSQL — Supabase recommended; SQLite only for tests
- **Cache + queue:** Redis, Celery (`time_limit` / `soft_time_limit` / `acks_late`)
- **Event bus:** NATS JetStream (transactional outbox publisher)
- **LLM providers:** OpenAI / Anthropic / Ollama / Mock — selected by `settings.MORPHEUS_LLM_PROVIDER`
- **Observability:** OpenTelemetry → OTLP collector → Prometheus / Grafana / Loki + Sentry
- **Containers:** multi-stage Dockerfile, non-root, gunicorn runtime, k8s manifests
- **SDK:** [`services/sdk_python`](services/sdk_python/) — `pip install -e services/sdk_python`

---

## Security defaults (changed from a vanilla Django template)

- `DEBUG = False` by default. `SECRET_KEY`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `DATABASE_URL` are required in non-test envs.
- DRF default permission is `IsAuthenticated`; storefront catalog opts in to `AllowAny` explicitly.
- All webhooks ship with `X-Morpheus-Signature: sha256=<hmac>`.
- GraphQL has depth + alias caps (`GRAPHQL_MAX_QUERY_DEPTH`, `GRAPHQL_MAX_ALIASES`) and a `_MaskUnhandledErrors` extension.
- DRF + GraphQL exception handlers mask 5xx, surface `request_id`.
- `RateLimitMiddleware` wired on `/graphql` and `/v1/`. **Per-user rate limit on the agent invoke endpoint** (20 req/min/user).
- `IGNORE_EXCEPTIONS` on Redis cache — a Redis blip can't 500 the site.
- `SECURE_PROXY_SSL_HEADER` set to honor `X-Forwarded-Proto` from Plesk / Traefik / any TLS terminator.
- Sentry `before_send` scrubs auth tokens, cookies, and any password / secret / token / card key.
- **`@safe_db` decorator** for paths where DB outage should degrade gracefully (audit logging, telemetry mirroring) instead of crashing the request.
- **RBAC capabilities** — `rbac.has_capability(user, 'orders.refund', channel=ch)` for fine-grained access checks. Grants/revokes are audit-logged.

---

## Documentation

- [`SKILLS.md`](SKILLS.md) — **named procedures** for every common task (add a plugin, fix N+1, deploy to Coolify, …). Start here.
- [`docs/PLUGIN_DEVELOPMENT.md`](docs/PLUGIN_DEVELOPMENT.md) — full plugin developer guide.
- [`docs/THEME_DEVELOPMENT.md`](docs/THEME_DEVELOPMENT.md) — full theme developer guide.
- [`docs/deploy-coolify.md`](docs/deploy-coolify.md) — Coolify deployment.
- [`docs/deploy-plesk-nginx.md`](docs/deploy-plesk-nginx.md) — Plesk Nginx → Coolify Traefik reverse proxy config.
- [`docs/OPERATIONS_RUNBOOK.md`](docs/OPERATIONS_RUNBOOK.md) — backups, restore, deploy chain, on-call basics.
- [`RULES.md`](RULES.md) — the platform's immutable laws. Read before PR.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — system design, plugin lifecycle, the four pillars.
- [`AI_VISION.md`](AI_VISION.md) — strategic thesis.
- [`CHANGELOG.md`](CHANGELOG.md) — every shipped PR by phase.

---

## Contributing

PRs welcome. The bar:

1. **New behavior comes with tests.** The whole suite is fast — keep it that way.
2. **Don't add a top-level Django app for a new domain — make it a plugin** ([Skill: add a new plugin](SKILLS.md#skill-add-a-new-plugin)).
3. **Don't catch broad `Exception` without `exc_info=True` + a one-line reason.**
4. **Honor the security defaults** in [`morph/settings.py`](morph/settings.py).
5. **Operational pages → main sidebar; persistent config → settings panel.** Don't pollute settings with operational knobs.
6. **The change is reachable from a [skill in `SKILLS.md`](SKILLS.md)** — add or update one in the same PR if it isn't.

---

## Changelog

See [`CHANGELOG.md`](CHANGELOG.md) for the full history. Recent waves:

- **Phase 5** (2026-04-26) — PaymentGateway abstraction, Promotions v2 (rule-based), Draft Orders, Multi-warehouse allocator, Background agents lifecycle, Audit log, `safe_db` decorator, AI Signals reframe, Backups, Per-user rate limit, Bulk CSV, Embeddings → core, **Skills**, Agent observability dashboard, Settings UX cleanup. **PRs #42–#50.**
- **Phase 4** (2026-04-25) — Customer account v2, i18n, Channels, RBAC. PRs #38–#41.
- **Phase 3** (2026-04-23) — `gift_cards`, `b2b`, `subscriptions`. PR #29.
- **Phase 2** (2026-04-22) — webhooks UI, back-in-stock, scheduled prices, abandoned carts. PR #28.
- **Phase 1** (2026-04-22) — `tax`, `shipping`, refunds/RMA, `wishlist`. PR #23.

---

## License

MIT. Build whatever you want with it.

<div align="center">
<sub>Built by people who think AI agents deserve a real commerce platform, not a chatbot tab.</sub>
</div>
