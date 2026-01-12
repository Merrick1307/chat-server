import logging
import orjson
import sys

from typing import Optional
from contextvars import ContextVar

_current_error_logger: ContextVar[Optional['ErrorLogger']] = ContextVar('current_error_logger', default=None)


class ErrorLogger:
    """Logger for system errors, exceptions, and debugging."""

    def __init__(self, name: str = "error"):
        self.name = name
        self.logger = logging.getLogger(f"error.{name}")
        self.logger.setLevel(logging.INFO)
        self.logger.handlers.clear()
        self.logger.propagate = False

        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(logging.INFO)

        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - '
            '%(module)s:%(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str, **kwargs):
        """Log info message."""
        extra_str = f" | {orjson.dumps(kwargs).decode()}" if kwargs else ""
        self.logger.info(f"{message}{extra_str}")

    def warning(self, message: str, **kwargs):
        """Log warning message."""
        extra_str = f" | {orjson.dumps(kwargs).decode()}" if kwargs else ""
        self.logger.warning(f"{message}{extra_str}")

    def error(self, message: str, **kwargs):
        """Log error message."""
        extra_str = f" | {orjson.dumps(kwargs).decode()}" if kwargs else ""
        self.logger.error(f"{message}{extra_str}")

    def critical(self, message: str, **kwargs):
        """Log critical error."""
        extra_str = f" | {orjson.dumps(kwargs).decode()}" if kwargs else ""
        self.logger.critical(f"{message}{extra_str}")

    def debug(self, message: str, **kwargs):
        """Log debug message."""
        extra_str = f" | {orjson.dumps(kwargs).decode()}" if kwargs else ""
        self.logger.debug(f"{message}{extra_str}")

    def exception(self, message: str, exc: Exception, **kwargs):
        """Log exception with full traceback."""
        error_data = {
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            **kwargs
        }
        extra_str = f" | {orjson.dumps(error_data).decode()}"
        self.logger.exception(f"{message}{extra_str}", exc_info=exc)

    def log_system_error(self, context: str, error: Exception, **kwargs):
        """Log system error with context."""
        self.exception(
            f"System error in {context}",
            error,
            context=context,
            **kwargs
        )

    def log_database_error(self, operation: str, error: Exception, **kwargs):
        """Log database error."""
        self.exception(
            f"Database error during {operation}",
            error,
            operation=operation,
            **kwargs
        )

    def log_external_api_error(self, service: str, error: Exception, **kwargs):
        """Log external API error."""
        self.exception(
            f"External API error with {service}",
            error,
            service=service,
            **kwargs
        )


def get_error_logger() -> ErrorLogger:
    """Get the current request's error logger."""
    logger = _current_error_logger.get()
    if logger is None:
        raise RuntimeError("Error logger not initialized for current request")
    return logger