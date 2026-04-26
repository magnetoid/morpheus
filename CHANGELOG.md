# Changelog

All notable changes to Morpheus. Loose [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Dates are YYYY-MM-DD.

## [Unreleased]

### Phase 5 — Saleor parity + agent layer maturation (2026-04-26)

#### Added

- **`PaymentGateway` ABC + `GatewayRegistry`** ([PR #42](https://github.com/magnetoid/morpheus/pull/42))
  Drop-in slot for additional providers (PayPal, Payoneer, Adyen). Stripe
  and Manual adapters ship by default; registered in `PaymentsPlugin.ready()`.
- **Promotion engine v2** ([PR #43](https://github.com/magnetoid/morpheus/pull/43))
  New `promotions` plugin with `Promotion` (channel-scoped, time-bounded),
  `PromotionRule` (JSON predicates × actions), `PromotionApplication`
  (audit). Stacks predicates (`min_subtotal`, `currencies`, `countries`,
  `customer_groups`, `product_ids`, `first_order`) with actions
  (`percent_off`, `fixed_off`, `free_shipping`, `gift`). Hooks into
  `cart.calculate_total`. Decoupled from flat `marketing.Coupon` (codes
  can act as gates via `Promotion.requires_coupon`).
- **Draft orders + multi-warehouse allocator** ([PR #44](https://github.com/magnetoid/morpheus/pull/44))
  New `draft_orders` plugin (`DraftOrder` + `DraftOrderLine`,
  `services.recalc`, `services.convert_to_order`). `inventory.allocator.plan_allocation()`
  splits a desired qty across warehouses (`descending_stock` /
  `single_warehouse` / `default_first` strategies, optional preferred
  warehouse code). `InventoryService.reserve_for_order` now writes one
  `StockMovement` per (variant, warehouse) split.
- **Background agents lifecycle** ([PR #45](https://github.com/magnetoid/morpheus/pull/45))
  `BackgroundAgent` model + `scheduler.tick()` fired every minute via
  Celery beat (`agent_core.background_agents_tick`). Runs reuse the
  existing `run_agent` path so trace lands in `AgentRun`/`AgentStep`.
  Auto-pause after `max_failures_before_pause` (default 5). Reschedules
  before fire so concurrent beats can't double-run. Dashboard at
  `/dashboard/agents/background/` (run-now / pause / resume / delete /
  schedule).
- **Audit log + `safe_db` decorator + AI Signals reframe** ([PR #46](https://github.com/magnetoid/morpheus/pull/46))
  New `core.audit` engine app: `AuditEvent` model + `record(...)` helper.
  Tamper-evident "who changed what, when". First wiring: RBAC grant/revoke
  emits `rbac.role_granted` / `rbac.role_revoked`. New `core.utils.safe_db`
  decorator wraps a function so `DatabaseError` doesn't crash the caller
  (returns a default + logs). `ai_assistant` reframed as **AI Signals**
  (embeddings / search / recommendations / dynamic pricing) — agent
  runtime explicitly belongs in `core.agents` + `agent_core` from now on.
- **Backups + per-user rate limit + bulk CSV products** ([PR #47](https://github.com/magnetoid/morpheus/pull/47))
  `python manage.py morph_backup` — pg_dump (or sqlite copy) + media tar
  to `MORPHEUS_BACKUP_DIR` with retention. New `core.utils.rate_limit`
  module — sliding-window per-key limiter on Django cache. Wired into
  `agent_core.invoke_agent_view` at 20 req/min/user. New
  `importers.adapters.csv_products` — idempotent bulk CSV import (upsert
  by SKU, fall back to slug) + `export_products_csv()`. Dashboard at
  `/dashboard/import/csv/` under Catalog.
- **Embeddings → core, Skills, agent observability dashboard** ([PR #48](https://github.com/magnetoid/morpheus/pull/48))
  `core.embeddings` (promoted from `ai_assistant.services.embeddings` —
  identical surface; old module is a re-export shim). New
  `core.agents.Skill` — labeled bundles of tools + optional system-prompt
  prelude. Agents opt in via `uses_skills = ('skill_name', ...)`. Plugins
  ship via `contribute_skills()`. Replaces "re-declare the tool list on
  every agent" pattern. Observability dashboard at
  `/dashboard/agents/observability/` — runs / tokens / tool calls / avg
  duration over 1/7/30/90-day windows, state breakdown, top tools, recent
  failures.

#### Fixed

- **Settings double-menu** ([PR #49](https://github.com/magnetoid/morpheus/pull/49))
  Settings page was rendering its own left rail on top of the main
  sidebar's settings-mode nav. Removed the inner aside; deep-link via hash
  (`#pane=core-store`) still opens the right pane.
- **DashboardPage kwargs + settings-panel triage** ([PR #50](https://github.com/magnetoid/morpheus/pull/50))
  Five plugins (`promotions`, `draft_orders`, `importers`, `agent_core`,
  `demo_data`) were passing unsupported `url=` / `description=` kwargs to
  `DashboardPage`, silently dropping sidebar entries. Switched to the
  supported `view=` dotted-path form. Dropped trivial settings panels:
  `promotions` (operational data, not config) and `demo_data` (now a
  proper main-menu page under Catalog). **Settings now contains only
  panels with meaningful permanent configuration.**

#### Changed

- **33 plugins** active by default (was 30) — adds `promotions`,
  `draft_orders`, `rbac` already-merged-but-now-fully-wired.
- `MorpheusAgent.get_tools()` and `get_system_prompt()` resolve
  opted-in Skills from `skill_registry` and union them in.
- `MorpheusPlugin` now exposes `contribute_skills()` alongside
  `contribute_agent_tools()` / `contribute_agents()`.
- `RoleBinding` grants/revokes are audit-logged.
- README rewritten to surface the agent layer + Skills + Saleor parity
  + the operational-vs-config menu distinction.

---

### Phase 4 — Saleor-parity foundations (2026-04-25)

- **Customer account v2** (PR #38) — orders, addresses, returns, profile.
- **i18n kernel** (PR #39) — `core.i18n` with generic-FK `Translation` rows,
  `{{ obj|trans:"field" }}` filter, `i18n.translate_product` agent tool.
- **Channels wiring** (PR #40) — `StoreChannel` resolved by request host,
  `ProductChannelListing` for per-channel pricing, `core.channels.price_for`.
- **RBAC** (PR #41) — `Role` (slug + capabilities list) + `RoleBinding`,
  6 system role templates, `has_capability(user, cap, channel=None)`.

---

### Earlier in this Unreleased window

- **Hard-coded Morpheus Assistant in core** ([`core/assistant/`](core/assistant/)) —
  single always-available operator. System-level tools (filesystem read,
  DB introspection, log search, plugin status, server info, git log).
  Delegates to specialised agents via `delegate.invoke_agent`. Mounted at
  `/admin/assistant/` outside the plugin layer. JSONL fallback persistence
  when DB is down. Floating chat widget on every admin page.
- **Unified Settings hub** at `/dashboard/settings/` — sliding-panel
  layout with platform sections (Store / AI / Theme) plus every plugin's
  contributed `SettingsPanel`.
- **Phase 3 commerce plugins** (PR #29): `gift_cards`, `b2b`
  (quotes / per-account price lists / Net 15-90 terms), `subscriptions`
  (Plan + Subscription + invoice; Stripe Billing adapter slot).
- **Multi-currency display**: `core.ExchangeRate` model + display
  currency context processor + `{{ price|convert:DISPLAY_CURRENCY }}`
  template filter.
- **Search facets**: storefront `product_list` filters by category, tag,
  price range, and sort.
- **Phase 2 ops bundle** (PR #28): `webhooks_ui` with delivery log +
  retry/replay; `inventory.notify_back_in_stock`;
  `inventory.apply_price_schedules` + `catalog.PriceSchedule`;
  `inventory.find_abandoned_carts`; cart-recovery email task in marketing
  (idempotent stamp on `cart.metadata`).

---

## [0.1.0] — 2026-04-26

First tagged release. Live at [`dotbooks.store`](https://dotbooks.store/).

### Highlights

- **26 plugins** activate by default. Contribution surfaces: hooks, storefront blocks, dashboard pages, settings panels, **agents, agent tools**.
- **Kernel agent layer** (`core/agents/`) — peer of `core/hooks` and `plugins/`. Real LLM tool-use loop with provider abstraction (OpenAI / Anthropic / Ollama / Mock), versioned prompts, capability scopes, lossless trace.
- **5 built-in agents** — Concierge (storefront), Merchant Ops (admin), Pricing (system), Content Writer (merchant), Account Manager (CRM).
- **dot books** theme (`themes/library/dot_books/`) — modern editorial bookstore, the default storefront.
- **End-to-end checkout** — cart → order → inventory reservation → confirmation email → payment intent.
- **Production deploy chain** — Docker image baked with collected static, deployable on Coolify, Plesk Nginx reverse proxy supported.

### Plugins added (26 total)

Core commerce: `catalog`, `orders`, `customers`, `payments`, `inventory`, `marketing`, `analytics`, `storefront`, `admin_dashboard`, `tax` *(new)*, `shipping` *(new)*, `wishlist` *(new)*.

Agent layer: `agent_core` *(new)*, `ai_assistant`, `ai_content`, `functions`.

Growth: `affiliates`, `marketplace`, `crm` *(new)*, `loyalty_points`, `reviews`.

Ops/infra: `cloudflare`, `seo`, `observability`, `environments`, `importers`, `demo_data`, `advanced_ecommerce`.

### Recent merged PRs

- **#24** `feat(phase 4 + affiliates)` — security audit fixes (audience guard, LLM timeout, audit-incomplete flag, mutable-default fix, inventory race, Stripe idempotency) + full affiliate dashboard/agent surfaces.
- **#23** `feat(phase 1)` — tax + shipping + refunds/RMA + wishlist plugins.
- **#22** `feat(storefront)` — default pages (about / journal / account / etc.) + static-in-image fix for Django admin.
- **#21** `fix(storefront)` — normalise GraphQL camelCase to snake_case for dot_books templates.
- **#20** `fix(theme)` — dot_books base.html missing `{% load morph %}` for `storefront_blocks` tag.
- **#19** `feat(crm)` — CRM plugin (leads, accounts, deals, interactions, tasks, AccountManager agent) + deploy fixes (healthcheck, beat schedule, MD5 hasher in tests).
- **#18** `fix(cd)` — build on push to main + align image name with deploy.
- **#17** `fix(deploy)` — make Postgres sslmode operator-controlled.
- **#16** `feat(agents)` — kernel agent layer + agent_core plugin (4 built-in agents).
- **#15** `feat(plugins)` — advanced_ecommerce bundle demonstrating contribution surfaces.
- **#14** `feat(plugins)` — contribution surfaces (storefront blocks, dashboard pages, settings panels).
- **#13** `feat(checkout)` — working end-to-end checkout flow.
- **#12** `feat(observability)` — Sentry + request_id + structured logs + masked errors.
- **#11** `feat(plugins)` — `demo_data` plugin + `morph_seed_demo`.
- **#10** `feat(themes)` — theming SDK + scaffolder + developer guide.
- **#9** `feat(plugins)` — SEO plugin.
- **#8** `feat(themes)` — `dot_books` theme; set as default.
- **#7** `feat(plugins)` — plugin SDK + scaffolder + developer guide.
- **#6** `feat(dashboard)` — Shopify-style admin refresh.
- **#5** `feat(plugins)` — Cloudflare plugin.

### Roadmap (queued)

- **Phase 2** — webhooks subscriber UI, abandoned-cart emails, back-in-stock subs, scheduled price changes, bulk CSV import/export.
- **Phase 3** — B2B (quotes / net-terms / per-account price lists), subscriptions, gift cards, multi-currency, search facets.
