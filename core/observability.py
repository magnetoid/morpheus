"""OpenTelemetry initialization. Optional: if OTEL_EXPORTER_OTLP_ENDPOINT is unset,
this is a no-op. If set, we configure tracing exporters and instrument the
common Django/Celery/Redis stack."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger('morpheus.observability')


def init_observability() -> None:
    endpoint = os.getenv('OTEL_EXPORTER_OTLP_ENDPOINT')
    if not endpoint:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.celery import CeleryInstrumentor
        from opentelemetry.instrumentation.django import DjangoInstrumentor
        from opentelemetry.instrumentation.logging import LoggingInstrumentor
        from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
        from opentelemetry.instrumentation.redis import RedisInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError as e:
        logger.warning("OpenTelemetry not fully installed; tracing disabled: %s", e)
        return

    try:
        service_name = os.getenv('OTEL_SERVICE_NAME', 'morpheus')
        resource = Resource.create({'service.name': service_name})

        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=f"{endpoint.rstrip('/')}/v1/traces")
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        DjangoInstrumentor().instrument()
        RequestsInstrumentor().instrument()
        Psycopg2Instrumentor().instrument()
        RedisInstrumentor().instrument()
        LoggingInstrumentor().instrument(
            set_logging_format=True,
            logging_format=(
                '%(asctime)s %(levelname)s [%(name)s] '
                '[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s '
                'resource.service.name=%(otelServiceName)s] - %(message)s'
            ),
        )
        CeleryInstrumentor().instrument()
        logger.info("OpenTelemetry initialized: %s", endpoint)
    except Exception as e:  # noqa: BLE001 — observability must never break the app
        logger.error("OpenTelemetry initialization failed: %s", e, exc_info=True)
