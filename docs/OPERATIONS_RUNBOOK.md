# Morpheus — Operations Runbook

## Local Development (Containers)

- `docker-compose.yml` provides Postgres, Redis, NATS, OpenTelemetry Collector, Prometheus, Grafana.
- Web runs on `http://localhost:8000/`
- GraphQL runs on `http://localhost:8000/graphql/`
- Grafana runs on `http://localhost:3000/` (admin/admin)

## Health and Readiness

- `GET /healthz` liveness
- `GET /readyz` readiness (DB + cache)

## Kubernetes Deployment

- Apply manifests under `k8s/`.
- Ensure secrets are set in `k8s/secret.yaml` (or your secret manager).
- Use rolling updates for zero-downtime.

## Scaling

- Web uses `k8s/hpa-web.yaml` (CPU 60%, min 2, max 10).
- Prefer request-based scaling via KEDA for queues/event lag when available.

## Observability

- Traces are exported via OTLP to the collector.
- Collector exposes Prometheus metrics at `:8889`.
- Grafana is provisioned with a Prometheus datasource.

## Autonomous Ops (Advisory Mode)

- `ops-agent` exposes `GET /recommendations` for policy suggestions.
- Upgrade path: apply policies via GitOps PRs (preferred) or Kubernetes API.

