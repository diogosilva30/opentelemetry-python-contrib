import logging
import os

from celery import Celery
from celery.signals import celeryd_after_setup, worker_process_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myproject.settings")

logging.getLogger("opentelemetry.instrumentation.celery").setLevel(logging.DEBUG)

app = Celery("myproject")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


def _create_meter_provider():
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": "celery-example"})
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(),
        export_interval_millis=5000,
    )
    return MeterProvider(resource=resource, metric_readers=[metric_reader])


@celeryd_after_setup.connect(weak=False)
def init_worker_metrics(sender, instance, conf, **kwargs):
    """Set up worker-level metrics in the main worker process."""
    from opentelemetry.instrumentation.celery import CeleryWorkerInstrumentor

    CeleryWorkerInstrumentor().instrument(meter_provider=_create_meter_provider())
    print(f"[OTel] CeleryWorkerInstrumentor active for {sender}")


@worker_process_init.connect(weak=False)
def init_celery_tracing(*args, **kwargs):
    """Set up tracing + task metrics in each worker subprocess."""
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
    )

    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    resource = Resource.create({"service.name": "celery-example"})

    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter())
    )

    CeleryInstrumentor().instrument(
        tracer_provider=tracer_provider,
        meter_provider=_create_meter_provider(),
    )
    print("[OTel] CeleryInstrumentor active in worker subprocess")
