# Plugin Development Guide

> Full developer reference for building Morpheus plugins.
> For named, repeatable procedures see [`SKILLS.md`](../SKILLS.md).
> For platform-wide laws see [`RULES.md`](../RULES.md).

Morpheus is a **plugin-native engine**. The core does almost nothing on its
own — it discovers plugins, builds the URL map and GraphQL schema from them,
runs hooks across them, and otherwise gets out of the way.

This guide is your end-to-end map for shipping production-quality plugins.

---

## Table of contents

1. [Quick start (60 seconds)](#1-quick-start-60-seconds)
2. [Anatomy of a plugin](#2-anatomy-of-a-plugin)
3. [The lifecycle](#3-the-lifecycle)
4. [Metadata reference](#4-metadata-reference)
5. [Extension points](#5-extension-points)
6. [Models, migrations, indexes](#6-models-migrations-indexes)
7. [GraphQL — queries, mutations, permissions](#7-graphql--queries-mutations-permissions)
8. [URLs and views](#8-urls-and-views)
9. [Hooks and events](#9-hooks-and-events)
10. [Background tasks (Celery)](#10-background-tasks-celery)
11. [Configuration schema](#11-configuration-schema)
12. [Multi-tenancy / channel scoping](#12-multi-tenancy--channel-scoping)
13. [Testing](#13-testing)
14. [Distribution as a community plugin](#14-distribution-as-a-community-plugin)
15. [Cookbook](#15-cookbook)

---

## 1. Quick start (60 seconds)

```bash
python manage.py morph_create_plugin discount_engine \
    --label "Discount Engine" \
    --description "Per-customer discount rules." \
    --with-models --with-graphql --with-tasks
```

This generates:

```
plugins/installed/discount_engine/
├── __init__.py
├── apps.py
├── plugin.py            ← MorpheusPlugin subclass
├── models.py            ← starter model
├── tasks.py             ← starter Celery task
├── graphql/
│   └── queries.py       ← Strawberry mixin
├── migrations/
│   └── __init__.py
└── tests/
    └── test_smoke.py
```

Then:

```bash
# 1. Add 'plugins.installed.discount_engine' to MORPHEUS_DEFAULT_PLUGINS in morph/settings.py
# 2. Generate the migration:
python manage.py makemigrations discount_engine
python manage.py migrate

# 3. Verify:
python manage.py check                # plugin appears in the activation log
python manage.py test plugins.installed.discount_engine
```

That's it — the plugin is live.

---

## 2. Anatomy of a plugin

```
plugins/installed/<name>/
├── __init__.py             # default_app_config -> apps.<NameConfig>
├── apps.py                 # Django AppConfig (label = <name>)
├── plugin.py               # ★ MorpheusPlugin subclass: the manifest
├── models.py               # optional: Django models
├── migrations/
│   ├── __init__.py
│   └── 0001_initial.py
├── views.py                # optional: HTTP endpoints
├── urls.py                 # optional: URL config
├── tasks.py                # optional: Celery tasks
├── services.py             # ★ all business logic lives here
├── graphql/
│   ├── __init__.py
│   ├── queries.py          # <Plugin>QueryExtension
│   └── mutations.py        # <Plugin>MutationExtension
├── tests/
│   └── test_*.py
└── management/             # optional: Django management commands
    └── commands/
```

The **only required file** is `plugin.py`. Everything else is opt-in.

---

## 3. The lifecycle

```
                ┌──────────────────────────────────────────────┐
                │            settings.py boot                  │
                │ MORPHEUS_DEFAULT_PLUGINS + EXTRA_PLUGINS     │
                └─────────────────────┬────────────────────────┘
                                      ▼
                ┌──────────────────────────────────────────────┐
                │ plugin_registry.discover(paths)              │
                │   imports each <plugin>.plugin module        │
                │   discovers MorpheusPlugin subclass          │
                └─────────────────────┬────────────────────────┘
                                      ▼
                ┌──────────────────────────────────────────────┐
                │ plugin_registry.activate_all()  (AppReady)   │
                │   1. validate dependency graph               │
                │   2. topological sort by `requires`          │
                │   3. for each plugin in order: call ready()  │
                └─────────────────────┬────────────────────────┘
                                      ▼
                ┌──────────────────────────────────────────────┐
                │ Each ready() registers hooks, GraphQL,       │
                │ URLs, admin, tasks, beat schedule entries    │
                └──────────────────────────────────────────────┘
```

If `ready()` raises, **only that plugin** is deactivated — siblings keep loading.
The exception is logged with a full traceback (see `plugins/registry.py:_activate`).

---

## 4. Metadata reference

| Field | Type | Required | Purpose |
|---|---|---|---|
| `name` | `str` | ✅ | Snake_case identifier. **Must equal the directory name.** |
| `label` | `str` | ✅ | Human-readable name shown in the dashboard. |
| `version` | `str` | ✅ | PEP 440-style (e.g. `0.1.0`, `1.2.3a4`). |
| `description` | `str` | recommended | One-line what-it-does. |
| `author` | `str` | optional | Default `"Morph Team"`. |
| `url` | `str` | optional | Plugin homepage / docs. |
| `requires` | `list[str]` | optional | Plugin names this depends on (topological order). |
| `conflicts` | `list[str]` | optional | Plugins this cannot coexist with. |
| `has_models` | `bool` | ✅ if you have models | If True, the plugin needs to be in `INSTALLED_APPS`. |

The base class **validates** all metadata at class-definition time — typos
fail fast at import, not at runtime.

---

## 5. Extension points

All extension calls go inside `ready()`. They take effect once per process.

| Helper | What it does |
|---|---|
| `register_hook(event, handler, priority=50)` | Subscribe to a `MorpheusEvents.*` constant or any string. Lower priority runs first. |
| `register_graphql_extension(module)` | Module path of a class named `<X>QueryExtension` or `<X>MutationExtension`. |
| `register_urls(module, prefix='', namespace=name)` | Mount a URLconf module under a prefix. |
| `register_admin(Model, AdminCls)` | Register a Django admin entry. Idempotent. |
| `register_celery_tasks(module)` | Surface a tasks module to Celery autodiscovery. |
| `register_celery_beat(name, entry)` | Add a scheduled task entry (won't overwrite an existing one). |
| `register_context_processor(func)` | Add a template context processor. |

Calling any of these *outside* `ready()` raises a clear runtime error.

---

## 6. Models, migrations, indexes

* Use `UUIDField(primary_key=True, default=uuid.uuid4, editable=False)` — see [LAW 7](../RULES.md#law-7--all-primary-keys-are-uuids).
* Use `MoneyField` from `djmoney` for currency — see [LAW 6](../RULES.md#law-6--safe-money-and-immutable-states).
* State machines use `django-fsm` `FSMField` with `@transition` decorators.
* Index every field you `filter()` on: `db_index=True` for single columns, `models.Index(fields=[…])` in `Meta` for composites.
* Run `python manage.py makemigrations <plugin>` after every model change.
* Run `python manage.py makemigrations --check --dry-run` in CI to catch missing migrations.

See [`SKILLS.md` → Add a model](../SKILLS.md#skill-add-a-model).

---

## 7. GraphQL — queries, mutations, permissions

```python
# graphql/queries.py
import strawberry
from api.graphql_permissions import has_scope, require_authenticated

@strawberry.type
class DiscountEngineQueryExtension:

    @strawberry.field(description="Discount rules visible to the caller.")
    def discount_rules(self, info: strawberry.Info) -> list[str]:
        require_authenticated(info)
        if not has_scope(info, "read:discounts"):
            return []
        # … fetch + return
        return []
```

In `plugin.py`:

```python
def ready(self) -> None:
    self.register_graphql_extension(
        "plugins.installed.discount_engine.graphql.queries"
    )
```

Convention: the class name **must end in `QueryExtension` or
`MutationExtension`**. The schema assembler scans for these and merges them
into the root `Query` / `Mutation` types.

### Permission helpers

| Helper | Behavior |
|---|---|
| `require_authenticated(info)` | Raises `PermissionDenied` if no session/token/agent. |
| `has_scope(info, "read:foo")` | True for an admin staff user, an API key with the scope, or an agent with the scope. |
| `current_customer(info)` | Returns the logged-in user or `None`. |
| `current_channel_id(info)` | Returns the channel id from the API key / agent — for multi-tenancy filtering. |

`PermissionDenied` is mapped to a structured GraphQL error
(`extensions.code: PERMISSION_DENIED`) by the schema extension in `api/schema.py`.

### Eager-load to avoid N+1

```python
qs = (
    Order.objects
    .select_related("customer", "channel")
    .prefetch_related("items", "items__product", "events")
)
```

Add a regression test using `assertNumQueries(...)`.

---

## 8. URLs and views

```python
# urls.py
from django.urls import path
from . import views

app_name = "discount_engine"

urlpatterns = [
    path("", views.index, name="index"),
]
```

```python
# plugin.py
def ready(self) -> None:
    self.register_urls(
        "plugins.installed.discount_engine.urls",
        prefix="discounts/",
    )
```

URLs land at `/discounts/` (no leading slash on the prefix; Django adds it).

---

## 9. Hooks and events

Subscribe to **built-in events** from `core.hooks.MorpheusEvents` or define
your own. Custom events should be documented as constants in your plugin so
others can subscribe.

```python
from core.hooks import MorpheusEvents

def ready(self) -> None:
    self.register_hook(MorpheusEvents.ORDER_PLACED, self.on_order, priority=80)

def on_order(self, order, **kwargs):
    # Always accept **kwargs — the signature can grow.
    # Wrap the body in try/except to keep the chain alive on bad data.
    try:
        ...
    except Exception:
        import logging
        logging.getLogger("my_plugin").warning("hook failed", exc_info=True)
```

`hook_registry.fire(event, **kwargs)` ALSO writes a row to the `OutboxEvent`
table, which the Celery `process_outbox` task drains to NATS / webhooks.
That gives you exactly-once side-effect delivery for free.

See [LAW 4 in RULES.md](../RULES.md#law-4--plugins-communicate-via-hooks--outbox).

---

## 10. Background tasks (Celery)

```python
# tasks.py
from celery import shared_task

@shared_task(bind=True, time_limit=120, soft_time_limit=100)
def reprice_all_products(self):
    ...
```

Always set `time_limit` + `soft_time_limit` so a runaway task can't pin a
worker forever.

To schedule it periodically:

```python
# plugin.py
from celery.schedules import crontab

def ready(self) -> None:
    self.register_celery_beat(
        "discount_engine.reprice_hourly",
        {
            "task": "plugins.installed.discount_engine.tasks.reprice_all_products",
            "schedule": crontab(minute=15),
        },
    )
```

---

## 11. Configuration schema

Plugins can expose a JSON Schema; the merchant admin renders it as a form.

```python
def get_config_schema(self) -> dict:
    return {
        "type": "object",
        "properties": {
            "enable_dynamic_pricing": {
                "type": "boolean",
                "default": False,
                "title": "Enable dynamic pricing",
            },
            "max_discount_pct": {
                "type": "number", "minimum": 0, "maximum": 100, "default": 30,
            },
        },
    }
```

Read values:

```python
self.get_config_value("max_discount_pct", default=30)
```

`get_config()` is cached in-process; `set_config(key, value)` invalidates the cache.

---

## 12. Multi-tenancy / channel scoping

Every business model that is per-merchant should carry a nullable FK to
`core.StoreChannel`. The platform provides:

* **In GraphQL resolvers:** `current_channel_id(info)` resolves the channel
  from the authenticated API key / agent.
* **In REST viewsets:** `request._morpheus_api_key.channel_id` is set by
  `MorpheusAPIKeyAuthentication` on every authed request.
* **For routing:** the `EnvironmentMiddleware` on the request lets you scope
  by `Environment` for dev/staging/prod.

A typical scoped queryset looks like:

```python
qs = MyModel.objects.filter(channel_id=current_channel_id(info))
```

When `channel_id` is `None`, the row applies to **all channels**.

---

## 13. Testing

### Unit / integration

```python
from django.test import TestCase

class DiscountEngineTests(TestCase):
    def test_propose_creates_pending_rule(self):
        ...
```

Run:

```bash
python manage.py test plugins.installed.discount_engine
```

### Permission boundary tests (mandatory)

For any authed resolver / viewset, test all three cases:

1. Anonymous → empty result or 401/403.
2. Authenticated without scope → `PERMISSION_DENIED`.
3. Authenticated with scope → sees data.

See `api/tests.py:RestPermissionTests` for the canonical pattern.

### Query-count regression

```python
with self.assertNumQueries(2):
    list(my_resolver(...))
```

---

## 14. Distribution as a community plugin

Two paths.

### Path A — drop-in via `MORPHEUS_EXTRA_PLUGINS`

The merchant clones your plugin into `plugins/installed/<name>/` and adds
the path to:

```
MORPHEUS_EXTRA_PLUGINS=plugins.installed.<name>
```

That's it — the plugin auto-enables on first boot.

### Path B — pip-installable

Publish your plugin as a Python package on PyPI:

```
my_morph_plugin/
├── pyproject.toml
└── my_morph_plugin/
    ├── __init__.py
    ├── apps.py
    ├── plugin.py
    └── ...
```

Merchants then:

```bash
pip install my-morph-plugin
```

…and add `my_morph_plugin` to `MORPHEUS_EXTRA_PLUGINS`. The discovery
loop imports `<path>.plugin` regardless of where the package lives on disk.

**Naming convention:** prefix package names with `morph-` so they're
discoverable on PyPI.

---

## 15. Cookbook

### Add a custom event

```python
# In your plugin's services.py
from core.hooks import hook_registry, MorpheusEvents

# Document it as a constant for subscribers:
class DiscountEvents:
    DISCOUNT_APPLIED = "discount.applied"

# Fire it from your transition:
hook_registry.fire(DiscountEvents.DISCOUNT_APPLIED, cart=cart, amount=amount)
```

### React to an event from another plugin

```python
def ready(self) -> None:
    self.register_hook("discount.applied", self.on_discount, priority=90)

def on_discount(self, cart, amount, **kwargs):
    ...
```

### Add a Strawberry mutation that requires admin scope

```python
@strawberry.mutation(description="Create a discount rule (admin scope required).")
def create_discount_rule(self, info, input: CreateRuleInput) -> RuleType:
    require_authenticated(info)
    if not has_scope(info, "admin:discounts"):
        raise PermissionDenied("admin:discounts scope required")
    ...
```

### Schedule a daily rollup

```python
def ready(self) -> None:
    from celery.schedules import crontab
    self.register_celery_beat(
        "my_plugin.daily_rollup",
        {
            "task": "plugins.installed.my_plugin.tasks.rollup",
            "schedule": crontab(hour=0, minute=15),
        },
    )
```

### Drop into the merchant dashboard

The dashboard auto-renders **every active plugin** in its **Apps** view.
For a custom dashboard page, ship a Django view in your plugin and add a
sidebar entry by registering URLs under `dashboard/`:

```python
self.register_urls("plugins.installed.my_plugin.urls", prefix="dashboard/my_plugin/")
```

---

## See also

- [`SKILLS.md`](../SKILLS.md) — named, repeatable procedures (the "how").
- [`RULES.md`](../RULES.md) — platform laws (the "what's non-negotiable").
- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — the "why".
- [`plugins/base.py`](../plugins/base.py) — the source of truth for the base class.
- [`plugins/registry.py`](../plugins/registry.py) — discovery + activation engine.
