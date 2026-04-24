# Morpheus Engine

<div align="center">
  <p><strong>The first commerce platform built natively for AI Agents.</strong></p>
  <p>What Shopify would be if it were built today.</p>
</div>

---

## ⚡️ The Mission

Legacy platforms (Shopify, Magento, BigCommerce) were built for a world that no longer exists. They treat AI as an afterthought or a third-party API consumer.

**Morpheus is different.** We treat AI agents as the *primary audience*. Every feature, endpoint, and capability must be fully understandable and executable by an LLM before a human UI is ever built. 

By designing for agents first, we are forced to build cleaner schemas, stricter state machines, and more actionable error handling. The result is a platform that is infinitely scalable, horizontally extensible via a rigorous plugin architecture, and completely free from legacy vendor lock-in.

---

## ✨ Core Architecture

Morpheus is a lightweight engine powering a massive plugin ecosystem. The core contains almost no business logic—everything from Products to Orders to the AI Assistant itself is an isolated plugin.

### 🤖 1. Agentic-First Design
Every Morpheus instance auto-generates LLM tool manifests directly from the live GraphQL schema. Any LLM with tool-use can immediately shop, manage inventory, or run marketing campaigns with zero custom integration code.
- `GET /api/agent-tools/openai.json` → OpenAI function calling format
- `GET /api/agent-tools/anthropic.json` → Anthropic tool use format
- **Model Context Protocol (MCP)** support built-in natively.

### 🔌 2. 100% Plugin Driven
The core provides only infrastructure: Event Bus, Registry, Caching, and RBAC. 
If a feature can be removed and the engine still boots, it is a plugin.
- **Native Plugins:** Django apps living in `plugins/installed/`.
- **Remote Plugins:** External Node/Go/Rust microservices that subscribe to Morpheus via Webhooks (`WebhookEndpoint`).

### 🏗 3. Headless Multi-Tenancy
A single Morpheus backend deployment natively powers wholesale B2B channels, mobile apps, and B2C retail storefronts simultaneously via the `StoreChannel` scoping system.

### 🛡 4. Immutable Event Sourcing
Currency is handled safely via `MoneyField`. Order statuses transition strictly via Finite State Machines (`django-fsm`). Every financial transition generates an immutable `OrderEvent` for perfect auditability.

### 🚀 5. Event-Driven Redis Caching
Aggressive Redis query caching with Smart Invalidation. When a product updates, the `MorpheusEvents.PRODUCT_UPDATED` hook automatically flushes only the relevant cached GraphQL edges.

---

## 🛠 Tech Stack

- **Backend:** Python 3.12, Django 5+
- **Database:** PostgreSQL (Supabase recommended)
- **API:** Strawberry GraphQL + Django REST Framework (DRF)
- **Caching & Workers:** Redis + Celery
- **Payments:** Stripe natively integrated

---

## 🚀 Quick Start

### 1. Installation

Clone the repository and set up a virtual environment:

```bash
git clone https://github.com/magnetoid/morpheus.git
cd morpheus
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the root directory and configure your secrets:

```env
SECRET_KEY=your_secure_secret_key
DEBUG=True
DATABASE_URL=postgres://user:pass@localhost:5432/morpheus
REDIS_URL=redis://localhost:6379/0

# AI Provider Settings
AI_PROVIDER=openai
OPENAI_API_KEY=sk-your-key

# Payments
STRIPE_SECRET_KEY=sk_test_...
```

### 3. Migrate & Run

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Start the Celery worker for background tasks and webhook dispatching:
```bash
celery -A morph worker -l info
```

---

## 📖 Documentation

- **[Rules of the Platform](RULES.md)**: The 11 immutable laws of developing on Morpheus. Read this before submitting a PR.
- **[Architecture & Vision](ARCHITECTURE.md)**: Deep dive into the system design, plugin lifecycle, and data flow.

---

## 🤝 Contributing

We are building the future of commerce. If you believe that open-source, developer-owned, agent-native platforms will replace the walled gardens of today, we want your help. 

Please read `RULES.md` thoroughly before opening a Pull Request.

---

## 📄 License

Morpheus is open-source software licensed under the MIT License.
