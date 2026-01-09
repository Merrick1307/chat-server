from .errors import ErrorLogger, get_error_logger
from .dependencies import (
    get_error_logger_dependency,
    ErrorLoggerDep,
)

__all__ = [
    "ErrorLogger",
    "get_error_logger",
    "get_error_logger_dependency",
    "ErrorLoggerDep"
]
