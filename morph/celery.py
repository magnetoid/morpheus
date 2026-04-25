"""
Morpheus CMS — Celery Configuration
"""
import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'morph.settings')

app = Celery('morpheus')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

try:
    from core.observability import init_observability
    init_observability()
    from opentelemetry.instrumentation.celery import CeleryInstrumentor
    CeleryInstrumentor().instrument()
except Exception:
    pass


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
