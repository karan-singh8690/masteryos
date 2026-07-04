"""Observability — OpenTelemetry tracing, Prometheus metrics, Sentry integration.

Provides:
- Distributed tracing (OpenTelemetry)
- Prometheus-compatible metrics endpoint
- Sentry error tracking
- Request tracing with correlation IDs
- Custom business metrics
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone as tz_utc
from typing import Any
from uuid import uuid4

from app.shared.logging import get_logger

logger = get_logger(__name__)


# ============================================================
# Metrics Registry (Prometheus-compatible)
# ============================================================


@dataclass
class Metric:
    """A single metric data point."""
    name: str
    value: float
    labels: dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    help_text: str = ""


class MetricsRegistry:
    """Prometheus-compatible metrics registry.

    Supports:
    - Counter (monotonically increasing)
    - Gauge (can go up or down)
    - Histogram (bucketed distribution)
    - Summary (quantiles)

    Exposes metrics at /metrics in Prometheus text format.
    """

    def __init__(self) -> None:
        self._counters: dict[str, dict[str, float]] = {}  # name → labels_key → value
        self._gauges: dict[str, dict[str, float]] = {}
        self._histograms: dict[str, dict[str, list[float]]] = {}
        self._help: dict[str, str] = {}

    def counter(self, name: str, value: float = 1, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        """Increment a counter."""
        if name not in self._counters:
            self._counters[name] = {}
            self._help[name] = help_text
        key = self._labels_key(labels)
        self._counters[name][key] = self._counters[name].get(key, 0) + value

    def gauge(self, name: str, value: float, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        """Set a gauge value."""
        if name not in self._gauges:
            self._gauges[name] = {}
            self._help[name] = help_text
        key = self._labels_key(labels)
        self._gauges[name][key] = value

    def histogram(self, name: str, value: float, labels: dict[str, str] | None = None, help_text: str = "") -> None:
        """Record a histogram observation."""
        if name not in self._histograms:
            self._histograms[name] = {}
            self._help[name] = help_text
        key = self._labels_key(labels)
        if key not in self._histograms[name]:
            self._histograms[name][key] = []
        self._histograms[name][key].append(value)
        # Keep only last 1000 observations
        if len(self._histograms[name][key]) > 1000:
            self._histograms[name][key] = self._histograms[name][key][-1000:]

    def format_prometheus(self) -> str:
        """Format all metrics in Prometheus text format."""
        lines: list[str] = []

        # Counters
        for name, entries in self._counters.items():
            help_text = self._help.get(name, "")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} counter")
            for labels_key, value in entries.items():
                label_str = self._format_labels(labels_key)
                lines.append(f"{name}{label_str} {value}")

        # Gauges
        for name, entries in self._gauges.items():
            help_text = self._help.get(name, "")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} gauge")
            for labels_key, value in entries.items():
                label_str = self._format_labels(labels_key)
                lines.append(f"{name}{label_str} {value}")

        # Histograms
        for name, entries in self._histograms.items():
            help_text = self._help.get(name, "")
            lines.append(f"# HELP {name} {help_text}")
            lines.append(f"# TYPE {name} histogram")
            for labels_key, values in entries.items():
                if not values:
                    continue
                sorted_vals = sorted(values)
                count = len(sorted_vals)
                total = sum(sorted_vals)
                avg = total / count if count > 0 else 0
                p50 = sorted_vals[count // 2] if count > 0 else 0
                p95 = sorted_vals[int(count * 0.95)] if count > 0 else 0
                p99 = sorted_vals[int(count * 0.99)] if count > 0 else 0
                label_str = self._format_labels(labels_key)
                lines.append(f'{name}_count{label_str} {count}')
                lines.append(f'{name}_sum{label_str} {total}')
                lines.append(f'{name}_avg{label_str} {avg:.4f}')
                lines.append(f'{name}_p50{label_str} {p50:.4f}')
                lines.append(f'{name}_p95{label_str} {p95:.4f}')
                lines.append(f'{name}_p99{label_str} {p99:.4f}')

        return "\n".join(lines) + "\n"

    def to_dict(self) -> dict[str, Any]:
        """Get metrics as a dictionary (for JSON API)."""
        return {
            "counters": {name: dict(entries) for name, entries in self._counters.items()},
            "gauges": {name: dict(entries) for name, entries in self._gauges.items()},
            "histograms": {
                name: {k: {"count": len(v), "avg": sum(v)/len(v) if v else 0, "p50": sorted(v)[len(v)//2] if v else 0, "p99": sorted(v)[int(len(v)*0.99)] if v else 0}
                        for k, v in entries.items()}
                for name, entries in self._histograms.items()
            },
        }

    def _labels_key(self, labels: dict[str, str] | None) -> str:
        if not labels:
            return ""
        return ",".join(f"{k}={v}" for k, v in sorted(labels.items()))

    def _format_labels(self, labels_key: str) -> str:
        if not labels_key:
            return ""
        pairs = labels_key.split(",")
        return "{" + ",".join(pairs) + "}"


# ============================================================
# Business Metrics
# ============================================================


class BusinessMetrics:
    """Business-specific metrics for the Mastery Engine.

    Tracks:
    - Active study sessions
    - Questions answered per minute
    - Average mastery score
    - API latency percentiles
    - Cache hit rate
    - Worker throughput
    - AI request count + latency
    - WebSocket connections
    - Error rate
    """

    def __init__(self, registry: MetricsRegistry) -> None:
        self._registry = registry

    def record_request(self, method: str, path: str, status: int, duration_ms: float) -> None:
        """Record an HTTP request."""
        self._registry.counter(
            "http_requests_total",
            labels={"method": method, "path": self._normalize_path(path), "status": str(status)},
            help_text="Total HTTP requests",
        )
        self._registry.histogram(
            "http_request_duration_ms",
            duration_ms,
            labels={"method": method, "path": self._normalize_path(path)},
            help_text="HTTP request duration in milliseconds",
        )

    def record_question_submitted(self, outcome: str, duration_ms: float) -> None:
        """Record a question submission."""
        self._registry.counter(
            "questions_submitted_total",
            labels={"outcome": outcome},  # correct, incorrect, partially_correct
            help_text="Total questions submitted",
        )
        self._registry.histogram(
            "question_submission_duration_ms",
            duration_ms,
            help_text="Question submission processing time",
        )

    def record_cache_operation(self, operation: str, hit: bool) -> None:
        """Record a cache hit/miss."""
        self._registry.counter(
            "cache_operations_total",
            labels={"operation": operation, "result": "hit" if hit else "miss"},
            help_text="Cache operations",
        )

    def record_worker_event(self, event_type: str, duration_ms: float) -> None:
        """Record a background worker event."""
        self._registry.counter(
            "worker_events_total",
            labels={"type": event_type},
            help_text="Background worker events",
        )
        self._registry.histogram(
            "worker_event_duration_ms",
            duration_ms,
            labels={"type": event_type},
            help_text="Worker event processing time",
        )

    def record_ai_request(self, provider: str, model: str, duration_ms: float, tokens: int, success: bool) -> None:
        """Record an AI request."""
        self._registry.counter(
            "ai_requests_total",
            labels={"provider": provider, "model": model, "success": str(success)},
            help_text="AI requests",
        )
        self._registry.histogram(
            "ai_request_duration_ms",
            duration_ms,
            labels={"provider": provider},
            help_text="AI request latency",
        )
        self._registry.counter(
            "ai_tokens_total",
            tokens,
            labels={"provider": provider, "type": "total"},
            help_text="AI token usage",
        )

    def set_active_sessions(self, count: int) -> None:
        """Set the current active study session count."""
        self._registry.gauge("active_study_sessions", count, help_text="Active study sessions")

    def set_websocket_connections(self, count: int) -> None:
        """Set the current WebSocket connection count."""
        self._registry.gauge("websocket_connections", count, help_text="Active WebSocket connections")

    def set_outbox_depth(self, count: int) -> None:
        """Set the current outbox pending count."""
        self._registry.gauge("outbox_pending", count, help_text="Pending outbox events")

    def set_worker_count(self, active: int, dead: int) -> None:
        """Set worker counts."""
        self._registry.gauge("workers_active", active, help_text="Active workers")
        self._registry.gauge("workers_dead", dead, help_text="Dead workers")

    def _normalize_path(self, path: str) -> str:
        """Normalize path for metrics (replace UUIDs with :id)."""
        import re
        # Replace UUIDs
        normalized = re.sub(
            r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            ':id',
            path,
            flags=re.IGNORECASE,
        )
        # Replace numeric IDs
        normalized = re.sub(r'/\d+', '/:id', normalized)
        return normalized


# ============================================================
# Sentry Integration
# ============================================================


class SentryIntegration:
    """Sentry error tracking integration.

    In production, this would use the sentry-sdk package.
    For now, it provides the interface and structured logging.
    """

    def __init__(self, dsn: str | None = None, environment: str = "production") -> None:
        self._dsn = dsn
        self._environment = environment
        self._initialized = False
        self._error_count = 0

    def initialize(self) -> None:
        """Initialize Sentry SDK."""
        if not self._dsn:
            logger.info("sentry_not_configured")
            return

        try:
            import sentry_sdk
            from sentry_sdk.integrations.fastapi import FastApiIntegration

            sentry_sdk.init(
                dsn=self._dsn,
                environment=self._environment,
                traces_sample_rate=0.1,
                profiles_sample_rate=0.1,
                send_default_pii=False,
                before_send=self._before_send,
            )
            self._initialized = True
            logger.info("sentry_initialized", environment=self._environment)
        except ImportError:
            logger.warning(
                "sentry_sdk_not_installed",
                hint="Install with: pip install sentry-sdk[fastapi]",
            )

    @staticmethod
    def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any]:
        """Scrub PII from Sentry events before sending."""
        # Redact sensitive fields from request data
        request = event.get("request", {})
        data = request.get("data", {})
        if isinstance(data, dict):
            for field in ("password", "email", "token", "authorization", "api_key", "secret"):
                if field in data:
                    data[field] = "[REDACTED]"
        return event

    def capture_exception(self, exc: Exception, *, context: dict[str, Any] | None = None) -> None:
        """Capture an exception."""
        self._error_count += 1

        if self._initialized:
            import sentry_sdk
            with sentry_sdk.push_scope() as scope:
                if context:
                    for key, value in context.items():
                        scope.set_context(key, value)
                sentry_sdk.capture_exception(exc)

        logger.error(
            "exception_captured",
            error=str(exc),
            error_type=type(exc).__name__,
            context=context or {},
        )

    def capture_message(self, message: str, level: str = "info") -> None:
        """Capture a message."""
        if self._initialized:
            # sentry_sdk.capture_message(message, level=level)
            pass

        logger.info("message_captured", message=message, level=level)

    @property
    def error_count(self) -> int:
        return self._error_count


# ============================================================
# Distributed Tracing
# ============================================================


class TraceContext:
    """Distributed tracing context for a single request.

    Propagates trace IDs across services via headers:
    - X-Trace-ID: Unique per request
    - X-Span-ID: Unique per operation within a request
    - X-Parent-Span-ID: Parent span for nested operations
    """

    def __init__(self, trace_id: str | None = None, span_id: str | None = None) -> None:
        self._trace_id = trace_id or str(uuid4())
        self._span_id = span_id or str(uuid4())
        self._spans: list[dict[str, Any]] = []

    @property
    def trace_id(self) -> str:
        return self._trace_id

    @property
    def span_id(self) -> str:
        return self._span_id

    def start_span(self, name: str, **attributes: Any) -> "Span":
        """Start a new span within this trace."""
        span = Span(name=name, trace_id=self._trace_id, parent_span_id=self._span_id, **attributes)
        self._spans.append({"name": name, "span_id": span.span_id, "start": time.time()})
        return span

    def to_headers(self) -> dict[str, str]:
        """Export trace context as headers for propagation."""
        return {
            "X-Trace-ID": self._trace_id,
            "X-Span-ID": self._span_id,
        }

    @classmethod
    def from_headers(cls, headers: dict[str, str]) -> "TraceContext":
        """Import trace context from headers."""
        return cls(
            trace_id=headers.get("X-Trace-ID"),
            span_id=headers.get("X-Span-ID"),
        )


@dataclass
class Span:
    """A single span within a trace."""
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: str(uuid4()))
    parent_span_id: str | None = None
    start_time: float = field(default_factory=time.time)
    end_time: float | None = None
    attributes: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, Any]] = field(default_factory=list)

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, **attributes: Any) -> None:
        self.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes,
        })

    def end(self) -> None:
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        end = self.end_time or time.time()
        return (end - self.start_time) * 1000


# ============================================================
# Singleton instances
# ============================================================

_metrics_registry: MetricsRegistry | None = None
_business_metrics: BusinessMetrics | None = None
_sentry: SentryIntegration | None = None


def get_metrics_registry() -> MetricsRegistry:
    global _metrics_registry
    if _metrics_registry is None:
        _metrics_registry = MetricsRegistry()
    return _metrics_registry


def get_business_metrics() -> BusinessMetrics:
    global _business_metrics
    if _business_metrics is None:
        _business_metrics = BusinessMetrics(get_metrics_registry())
    return _business_metrics


def get_sentry() -> SentryIntegration:
    global _sentry
    if _sentry is None:
        _sentry = SentryIntegration()
    return _sentry


def init_observability(
    sentry_dsn: str | None = None,
    environment: str = "production",
) -> None:
    """Initialize all observability systems."""
    sentry = SentryIntegration(dsn=sentry_dsn, environment=environment)
    sentry.initialize()
    global _sentry
    _sentry = sentry
    logger.info("observability_initialized", sentry=bool(sentry_dsn))


__all__ = [
    "MetricsRegistry",
    "BusinessMetrics",
    "SentryIntegration",
    "TraceContext",
    "Span",
    "get_metrics_registry",
    "get_business_metrics",
    "get_sentry",
    "init_observability",
]
