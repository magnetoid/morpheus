# Morpheus — Microservices Architecture (AI-First)

## Goals

- Horizontally scalable, container-first services.
- Unified API interfaces for web/mobile/desktop via a stable API gateway.
- Event-driven communication for cross-service workflows.
- Autonomous operations: self-healing, autoscaling, and AI-driven optimization.

## Strangler Migration (Current → Target)

Morpheus currently runs as a Django plugin-based backend. The migration strategy is:

1. Treat the current Django app as the initial API gateway and system-of-record.
2. Introduce an event bus and outbox pattern for reliable event publication.
3. Extract bounded contexts into independently deployable services over time.

## Target Service Topology

- `api-gateway` (Django, current): GraphQL/REST, auth, schema introspection, storefront.
- `orders-service`: order workflow, state machine, payments orchestration.
- `catalog-service`: product catalog, search indexing, pricing.
- `inventory-service`: stock levels, reservations, atomic movements.
- `ai-orchestrator`: tools, RAG, personalization, prompt registry, autonomous agents.
- `event-router`: validates and routes events, supports replay and DLQ.
- `ops-agent`: consumes telemetry and recommends/apply policies via GitOps.

## Unified API Interfaces

- Primary: GraphQL (`/graphql/`) for agentic-first operations.
- Agent entrypoint: `/graphql/agent/` with capability-scoped tokens.
- Secondary: versioned REST (`/v1/`) for aggregators.

## Event-Driven Patterns

- Event bus (NATS/Kafka) for asynchronous workflows.
- Outbox pattern for DB→event publication.
- Idempotent consumers and at-least-once processing.

## Autonomous Operation

- Self-healing: liveness/readiness probes + Kubernetes restarts.
- Automated scaling: HPA (CPU) + optional KEDA (queue depth / event lag).
- AI-driven optimization: `ops-agent` reads Prometheus and proposes scaling/cache policies.

## Real-Time Data Processing

- Streaming: subscribe to event topics for analytics, fraud, recommendations.
- Realtime delivery: WebSocket/SSE gateway backed by event subscriptions.

