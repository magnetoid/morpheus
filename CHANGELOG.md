# Changelog

All notable changes to Morpheus. Loose [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Dates are YYYY-MM-DD.

## [Unreleased]

### Added

- **Hard-coded Morpheus Assistant in core** ([`core/assistant/`](core/assistant/)) —
  a single, always-available operator that survives plugin failure, has
  system-level tools (filesystem read, DB introspection, log search,
  plugin status, server info, git log), and delegates to specialised
  agents via `delegate.invoke_agent`. Mounted at `/admin/assistant/`
  outside the plugin layer. Persistence falls back to JSONL on disk
  when the DB is down so the chat is never unreachable. Floating chat
  widget included by default in every admin page.
- **Unified Settings hub** at `/dashboard/settings/` — sliding-panel
  layout with platform sections (Store / AI / Theme) plus every plugin's
  contributed `SettingsPanel` (Stripe, Cloudflare, SEO, CRM, Tax,
  Shipping, etc.) — each plugin owns its own page.
- **Phase 3 commerce plugins** (PR #29): `gift_cards`, `b2b`
  (quotes / per-account price lists / Net 15-90 terms), `subscriptions`
  (Plan + Subscription + invoice; Stripe Billing adapter slot).
- **Multi-currency display**: `core.ExchangeRate` model + display
  currency context processor + `{{ price|convert:DISPLAY_CURRENCY }}`
  template filter.
- **Search facets**: storefront `product_list` now filters by category,
  tag, price range, and sort.
- **Phase 2 ops bundle** (PR #28): `webhooks_ui` plugin with delivery log
  + retry/replay; `inventory.notify_back_in_stock` task + model;
  `inventory.apply_price_schedules` beat task + `catalog.PriceSchedule`
  model; `inventory.find_abandoned_carts` beat task; cart-recovery email
  task in marketing (idempotent stamp on `cart.metadata`).

### Changed

- **30 plugins** active by default (was 27).
- README + ARCHITECTURE rewritten to surface the Core/Assistant + agent
  kernel + plugin layering distinction.

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
