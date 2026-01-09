from typing import Annotated
from fastapi import Depends

from .errors import ErrorLogger


def get_error_logger_dependency() -> ErrorLogger:
    """
    Dependency for ErrorLogger.
    Creates a new logger instance for each request.
    Returns:
        ErrorLogger instance
    """
    return ErrorLogger()


ErrorLoggerDep = Annotated[ErrorLogger, Depends(get_error_logger_dependency)]