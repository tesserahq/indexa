import time
from typing import Optional

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.openmetrics.exposition import (
    CONTENT_TYPE_LATEST,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

INFO = Gauge("fastapi_app_info", "FastAPI application information.", ["app_name"])
REQUESTS = Counter(
    "fastapi_requests_total",
    "Total count of requests by method and path.",
    ["method", "path", "app_name"],
)
RESPONSES = Counter(
    "fastapi_responses_total",
    "Total count of responses by method, path and status codes.",
    ["method", "path", "status_code", "app_name"],
)
REQUESTS_PROCESSING_TIME = Histogram(
    "fastapi_requests_duration_seconds",
    "Histogram of requests processing time by path (in seconds)",
    ["method", "path", "app_name"],
)
EXCEPTIONS = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised by path and exception type",
    ["method", "path", "exception_type", "app_name"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Gauge of requests by method and path currently being processed",
    ["method", "path", "app_name"],
)

# Indexing metrics
INDEXING_EVENTS_TOTAL = Counter(
    "indexing_events_total",
    "Total count of indexing events by service and status",
    ["service", "status", "entity_type"],
)

INDEXING_DURATION_SECONDS = Histogram(
    "indexing_duration_seconds",
    "Histogram of indexing duration by entity type (in seconds)",
    ["entity_type", "provider"],
)

PROVIDER_OPERATIONS_TOTAL = Counter(
    "provider_operations_total",
    "Total count of provider operations by provider, operation, and status",
    ["provider", "operation", "status"],
)

PROVIDER_LATENCY_SECONDS = Histogram(
    "provider_latency_seconds",
    "Histogram of provider operation latency (in seconds)",
    ["provider", "operation"],
)

REINDEX_JOBS_TOTAL = Counter(
    "reindex_jobs_total",
    "Total count of reindex jobs by status",
    ["status"],
)

REINDEX_PROGRESS = Gauge(
    "reindex_progress",
    "Current progress of reindex jobs by job_id",
    ["job_id"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, app_name: str = "fastapi-app") -> None:
        super().__init__(app)
        self.app_name = app_name
        INFO.labels(app_name=self.app_name).inc()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        method = request.method
        # The route template is only known after routing: FastAPI >= 0.138
        # matches included routers through a wrapper without a ``path``, so
        # matching app.routes up front no longer yields the template.
        REQUESTS_IN_PROGRESS.labels(
            method=method, path="*", app_name=self.app_name
        ).inc()
        before_time = time.perf_counter()
        try:
            response = await call_next(request)
        except BaseException as e:
            path = self.get_path(request)
            if path is not None:
                REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
                EXCEPTIONS.labels(
                    method=method,
                    path=path,
                    exception_type=type(e).__name__,
                    app_name=self.app_name,
                ).inc()
                RESPONSES.labels(
                    method=method,
                    path=path,
                    status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                    app_name=self.app_name,
                ).inc()
            raise e from None
        finally:
            REQUESTS_IN_PROGRESS.labels(
                method=method, path="*", app_name=self.app_name
            ).dec()

        path = self.get_path(request)
        if path is None:
            # Not routed (for example rejected by authentication first):
            # never label metrics with raw request paths.
            return response

        after_time = time.perf_counter()
        # retrieve trace id for exemplar
        span = trace.get_current_span()
        trace_id = trace.format_trace_id(span.get_span_context().trace_id)
        REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
        REQUESTS_PROCESSING_TIME.labels(
            method=method, path=path, app_name=self.app_name
        ).observe(after_time - before_time, exemplar={"TraceID": trace_id})
        RESPONSES.labels(
            method=method,
            path=path,
            status_code=response.status_code,
            app_name=self.app_name,
        ).inc()
        return response

    @staticmethod
    def get_path(request: Request) -> Optional[str]:
        """Return the matched route template, or None if nothing was routed."""
        return getattr(request.scope.get("route"), "path", None)


def metrics(request: Request) -> Response:
    return Response(
        generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST}
    )


def setting_otlp(
    app: ASGIApp, app_name: str, endpoint: str, log_correlation: bool = True
) -> None:
    # Setting OpenTelemetry
    # set the service name to show in traces
    resource = Resource.create(attributes={"service.name": app_name})

    # set the tracer provider
    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)

    tracer.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint, insecure=True))
    )

    if log_correlation:
        LoggingInstrumentor().instrument(set_logging_format=True)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)
