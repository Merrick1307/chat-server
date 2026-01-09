from abc import ABC
from typing import Optional

from asyncpg import Connection

from app.utils.logs import ErrorLogger


class BaseController(ABC):
    """
    Abstract base class for all controller classes.
    
    Controllers handle HTTP request/response logic and delegate
    business logic to services.
    """
    
    def __init__(
        self,
        db: Connection,
        logger: Optional[ErrorLogger] = None
    ):
        self._db = db
        self._logger = logger
    
    @property
    def db(self) -> Connection:
        """Database connection."""
        return self._db
    
    @property
    def logger(self) -> Optional[ErrorLogger]:
        """Error logger instance."""
        return self._logger
    
    async def log_error(self, message: str, **kwargs) -> None:
        """Log an error if logger is available."""
        if self._logger:
            self._logger.error(message, **kwargs)
    
    async def log_info(self, message: str, **kwargs) -> None:
        """Log info if logger is available."""
        if self._logger:
            self._logger.info(message, **kwargs)
