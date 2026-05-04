"""
Distributed Tracing with OpenTelemetry

Enables tracing across API boundaries, validation, curriculum sync, and analytics
with automatic span creation and context propagation.

Supports:
- FastAPI/Starlette integration
- Database operations
- External service calls
- Custom business logic spans
"""

from typing import Optional, Callable, Any
import functools
import time
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum

from app.logging.structured_logging import (
    get_logger,
    set_trace_context,
    clear_trace_context,
    trace_id_var,
    span_id_var,
)


class SpanKind(str, Enum):
    """OpenTelemetry span kinds."""
    INTERNAL = "INTERNAL"
    SERVER = "SERVER"
    CLIENT = "CLIENT"
    PRODUCER = "PRODUCER"
    CONSUMER = "CONSUMER"


@dataclass
class Span:
    """Simplified span representation."""
    name: str
    kind: SpanKind
    start_time_ms: float
    end_time_ms: Optional[float] = None
    duration_ms: Optional[float] = None
    status: str = "UNSET"  # OK, ERROR, UNSET
    error_message: Optional[str] = None
    attributes: dict = None
    events: list = None
    
    def __post_init__(self):
        if self.attributes is None:
            self.attributes = {}
        if self.events is None:
            self.events = []
    
    def add_attribute(self, key: str, value: Any):
        """Add attribute to span."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: dict = None):
        """Add event to span."""
        self.events.append({
            'name': name,
            'timestamp': time.time(),
            'attributes': attributes or {}
        })
    
    def end(self):
        """Mark span as ended."""
        self.end_time_ms = time.time() * 1000
        if self.start_time_ms:
            self.duration_ms = self.end_time_ms - self.start_time_ms
    
    def set_error(self, error_message: str):
        """Mark span as having an error."""
        self.status = "ERROR"
        self.error_message = error_message


class TracingContext:
    """Thread-safe tracing context manager."""
    
    _spans: ContextVar[list] = ContextVar('spans', default=None)
    
    @classmethod
    def get_spans(cls) -> list:
        """Get current span stack."""
        spans = cls._spans.get()
        if spans is None:
            spans = []
            cls._spans.set(spans)
        return spans
    
    @classmethod
    def push_span(cls, span: Span):
        """Add span to stack."""
        spans = cls.get_spans()
        spans.append(span)
        cls._spans.set(spans)
    
    @classmethod
    def pop_span(cls) -> Optional[Span]:
        """Remove and return top span from stack."""
        spans = cls.get_spans()
        if spans:
            return spans.pop()
        return None
    
    @classmethod
    def current_span(cls) -> Optional[Span]:
        """Get current (top) span without removing."""
        spans = cls.get_spans()
        return spans[-1] if spans else None


class Tracer:
    """
    Simplified distributed tracer for ScholarLab.
    
    Integrates with structured logging and provides span creation/management.
    """
    
    def __init__(self, service_name: str = "scholarlab"):
        self.service_name = service_name
        self.logger = get_logger('scholarlab.tracing')
    
    def start_span(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        attributes: dict = None,
    ) -> Span:
        """
        Start a new span.
        
        Args:
            name: Span name
            kind: Span kind (internal, server, client, etc.)
            attributes: Initial attributes
        
        Returns:
            Span object
        """
        span = Span(
            name=name,
            kind=kind,
            start_time_ms=time.time() * 1000,
            attributes=attributes or {},
        )
        
        TracingContext.push_span(span)
        
        self.logger.debug(
            f"Span started: {name}",
            extra={
                'span_name': name,
                'span_kind': kind.value,
                'attributes': attributes
            }
        )
        
        return span
    
    def end_span(self, span: Optional[Span] = None) -> Optional[Span]:
        """
        End current or specified span.
        
        Args:
            span: Span to end (if None, uses current span)
        
        Returns:
            Ended span
        """
        if span is None:
            span = TracingContext.pop_span()
        else:
            # Remove from stack if present
            spans = TracingContext.get_spans()
            if span in spans:
                spans.remove(span)
        
        if span:
            span.end()
            
            self.logger.debug(
                f"Span ended: {span.name}",
                extra={
                    'span_name': span.name,
                    'duration_ms': span.duration_ms,
                    'status': span.status,
                    'attributes': span.attributes,
                }
            )
        
        return span
    
    def trace_async(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        record_result: bool = False,
    ):
        """
        Decorator for async functions to automatically create spans.
        
        Usage:
            @tracer.trace_async("operation_name")
            async def my_async_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            async def wrapper(*args, **kwargs) -> Any:
                span = self.start_span(
                    name=name,
                    kind=kind,
                    attributes={'function': func.__name__}
                )
                try:
                    result = await func(*args, **kwargs)
                    if record_result:
                        span.add_attribute('result', str(result))
                    return result
                except Exception as e:
                    span.set_error(str(e))
                    raise
                finally:
                    self.end_span(span)
            return wrapper
        return decorator
    
    def trace_sync(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        record_result: bool = False,
    ):
        """
        Decorator for sync functions to automatically create spans.
        
        Usage:
            @tracer.trace_sync("operation_name")
            def my_function():
                ...
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                span = self.start_span(
                    name=name,
                    kind=kind,
                    attributes={'function': func.__name__}
                )
                try:
                    result = func(*args, **kwargs)
                    if record_result:
                        span.add_attribute('result', str(result))
                    return result
                except Exception as e:
                    span.set_error(str(e))
                    raise
                finally:
                    self.end_span(span)
            return wrapper
        return decorator


# Global tracer instance
_global_tracer: Optional[Tracer] = None


def initialize_tracer(service_name: str = "scholarlab") -> Tracer:
    """Initialize and return global tracer."""
    global _global_tracer
    _global_tracer = Tracer(service_name)
    return _global_tracer


def get_tracer() -> Tracer:
    """Get global tracer instance."""
    global _global_tracer
    if _global_tracer is None:
        _global_tracer = Tracer()
    return _global_tracer


# ============================================================================
# API TRACING MIDDLEWARE
# ============================================================================

class TracingMiddleware:
    """FastAPI middleware for automatic request tracing."""
    
    def __init__(self, app, tracer: Optional[Tracer] = None):
        self.app = app
        self.tracer = tracer or get_tracer()
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware callable."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        # Extract HTTP info for tracing
        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")
        request_id = scope.get("headers", [])  # Could extract from headers
        
        # Start request span
        span = self.tracer.start_span(
            name=f"{method} {path}",
            kind=SpanKind.SERVER,
            attributes={
                'http.method': method,
                'http.url': path,
                'http.target': scope.get("query_string", b"").decode(),
            }
        )
        
        # Intercept send to capture response status
        async def send_with_tracing(message):
            if message["type"] == "http.response.start":
                status = message.get("status", 500)
                span.add_attribute("http.status_code", status)
                
                if status >= 400:
                    span.status = "ERROR"
            
            await send(message)
        
        # Call app and clean up
        try:
            await self.app(scope, receive, send_with_tracing)
        except Exception as e:
            span.set_error(str(e))
            raise
        finally:
            self.tracer.end_span(span)


# ============================================================================
# BOUNDARY-SPECIFIC TRACING HELPERS
# ============================================================================

class APITracer:
    """Helper for tracing API operations."""
    
    @staticmethod
    def span_for_request(method: str, path: str, **kwargs) -> Span:
        """Create span for HTTP request."""
        tracer = get_tracer()
        return tracer.start_span(
            name=f"api.{method.lower()}.{path.replace('/', '_')}",
            kind=SpanKind.SERVER,
            attributes=kwargs
        )


class ValidationTracer:
    """Helper for tracing validation operations."""
    
    @staticmethod
    def span_for_validation(validation_type: str, **kwargs) -> Span:
        """Create span for validation operation."""
        tracer = get_tracer()
        return tracer.start_span(
            name=f"validation.{validation_type}",
            kind=SpanKind.INTERNAL,
            attributes=kwargs
        )


class SyncTracer:
    """Helper for tracing curriculum sync operations."""
    
    @staticmethod
    def span_for_sync(operation: str, **kwargs) -> Span:
        """Create span for sync operation."""
        tracer = get_tracer()
        return tracer.start_span(
            name=f"sync.{operation}",
            kind=SpanKind.INTERNAL,
            attributes=kwargs
        )


class AnalyticsTracer:
    """Helper for tracing analytics operations."""
    
    @staticmethod
    def span_for_analysis(analysis_type: str, **kwargs) -> Span:
        """Create span for analytics operation."""
        tracer = get_tracer()
        return tracer.start_span(
            name=f"analytics.{analysis_type}",
            kind=SpanKind.INTERNAL,
            attributes=kwargs
        )
