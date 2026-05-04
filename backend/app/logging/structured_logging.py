"""
Centralized Structured Logging for ScholarLab

Provides JSON-structured logging with automatic context propagation,
trace IDs, span IDs, and user/request context for all API/validation/sync/analytics operations.

Log Levels:
- DEBUG: Detailed tracing information (feature calculations, intermediate steps)
- INFO: General informational messages (successful operations, state changes)
- WARNING: Warnings (rejected spoofing attempts, validation failures, anomalies)
- ERROR: Error conditions requiring investigation
- CRITICAL: System-level failures requiring immediate action
"""

import json
import logging
import sys
import time
from typing import Any, Dict, Optional
from datetime import datetime, timezone
from pythonjsonlogger import jsonlogger
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from uuid import uuid4

# Context variables for distributed tracing
trace_id_var: ContextVar[str] = ContextVar('trace_id', default=None)
span_id_var: ContextVar[str] = ContextVar('span_id', default=None)
user_id_var: ContextVar[str] = ContextVar('user_id', default=None)
request_id_var: ContextVar[str] = ContextVar('request_id', default=None)


@dataclass
class TraceContext:
    """Distributed trace context."""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary for JSON logging."""
        return asdict(self)


class StructuredJsonFormatter(jsonlogger.JsonFormatter):
    """
    Custom JSON formatter that includes context variables and structured fields.
    """
    
    def add_fields(self, log_record: Dict, record: logging.LogRecord, message_dict: Dict):
        """Add custom fields to log record."""
        super().add_fields(log_record, record, message_dict)
        
        # Timestamp in UTC ISO format
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat()
        
        # Logger name and level
        log_record['logger'] = record.name
        log_record['level'] = record.levelname
        
        # Process and thread info
        log_record['process_id'] = record.process
        log_record['thread_id'] = record.thread
        
        # Add distributed tracing context
        trace_id = trace_id_var.get()
        span_id = span_id_var.get()
        user_id = user_id_var.get()
        request_id = request_id_var.get()
        
        if trace_id:
            log_record['trace_id'] = trace_id
        if span_id:
            log_record['span_id'] = span_id
        if user_id:
            log_record['user_id'] = user_id
        if request_id:
            log_record['request_id'] = request_id
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)


class ContextualLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes context information in every log.
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add context to every log message."""
        extra = kwargs.get('extra', {})
        
        # Add trace context if not already present
        if 'trace_id' not in extra:
            trace_id = trace_id_var.get()
            if trace_id:
                extra['trace_id'] = trace_id
        
        kwargs['extra'] = extra
        return msg, kwargs


def configure_structured_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    include_console: bool = True,
) -> logging.Logger:
    """
    Configure structured JSON logging for the entire application.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file to write logs to
        include_console: Whether to also log to console
    
    Returns:
        Configured root logger
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = StructuredJsonFormatter(
        '%(timestamp)s %(level)s %(logger)s %(message)s',
        rename_fields={'asctime': 'timestamp'},
    )
    
    # Console handler
    if include_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
        except IOError as e:
            root_logger.warning(f"Could not open log file {log_file}: {e}")
    
    return root_logger


def get_logger(name: str) -> ContextualLoggerAdapter:
    """
    Get a logger with automatic context propagation.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        ContextualLoggerAdapter instance
    """
    logger = logging.getLogger(name)
    return ContextualLoggerAdapter(logger, {})


def set_trace_context(
    trace_id: Optional[str] = None,
    span_id: Optional[str] = None,
    parent_span_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> TraceContext:
    """
    Set distributed trace context for current request.
    
    Args:
        trace_id: Unique trace ID (generated if not provided)
        span_id: Current span ID (generated if not provided)
        parent_span_id: Parent span ID (optional)
        user_id: Current user ID (optional)
        request_id: HTTP request ID (optional)
    
    Returns:
        TraceContext object
    """
    trace_id = trace_id or f"trace_{uuid4().hex[:12]}"
    span_id = span_id or f"span_{uuid4().hex[:12]}"
    
    trace_id_var.set(trace_id)
    span_id_var.set(span_id)
    user_id_var.set(user_id)
    request_id_var.set(request_id)
    
    return TraceContext(
        trace_id=trace_id,
        span_id=span_id,
        parent_span_id=parent_span_id,
        user_id=user_id,
        request_id=request_id,
    )


def clear_trace_context():
    """Clear distributed trace context (call at end of request)."""
    trace_id_var.set(None)
    span_id_var.set(None)
    user_id_var.set(None)
    request_id_var.set(None)


class PerformanceMonitor:
    """Context manager for performance monitoring with automatic logging."""
    
    def __init__(
        self,
        logger: logging.LoggerAdapter,
        operation: str,
        log_level: str = "INFO",
        threshold_ms: Optional[float] = None,
    ):
        """
        Initialize performance monitor.
        
        Args:
            logger: Logger to use
            operation: Operation name
            log_level: Log level for output
            threshold_ms: Alert if duration exceeds threshold (optional)
        """
        self.logger = logger
        self.operation = operation
        self.log_level = getattr(logging, log_level.upper())
        self.threshold_ms = threshold_ms
        self.start_time: Optional[float] = None
        self.duration_ms: Optional[float] = None
    
    def __enter__(self):
        """Start timer."""
        self.start_time = time.perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timer and log performance."""
        if self.start_time:
            self.duration_ms = (time.perf_counter() - self.start_time) * 1000
            
            log_msg = f"Operation '{self.operation}' completed in {self.duration_ms:.2f}ms"
            
            # Check if exceeded threshold
            if self.threshold_ms and self.duration_ms > self.threshold_ms:
                log_msg += f" (EXCEEDED threshold of {self.threshold_ms}ms)"
                self.logger.log(
                    self.log_level,
                    log_msg,
                    extra={'duration_ms': self.duration_ms, 'threshold_ms': self.threshold_ms}
                )
            else:
                self.logger.log(
                    self.log_level,
                    log_msg,
                    extra={'duration_ms': self.duration_ms}
                )
        
        return False


# ============================================================================
# BOUNDARY-SPECIFIC LOGGERS
# ============================================================================

def get_api_logger() -> ContextualLoggerAdapter:
    """Logger for API layer operations."""
    return get_logger('scholarlab.api')


def get_auth_logger() -> ContextualLoggerAdapter:
    """Logger for authentication operations."""
    return get_logger('scholarlab.auth')


def get_validation_logger() -> ContextualLoggerAdapter:
    """Logger for validation operations (biometric, device, spatial)."""
    return get_logger('scholarlab.validation')


def get_sync_logger() -> ContextualLoggerAdapter:
    """Logger for curriculum sync operations."""
    return get_logger('scholarlab.sync')


def get_analytics_logger() -> ContextualLoggerAdapter:
    """Logger for analytics and ML operations."""
    return get_logger('scholarlab.analytics')


def get_security_logger() -> ContextualLoggerAdapter:
    """Logger for security-related events."""
    return get_logger('scholarlab.security')
