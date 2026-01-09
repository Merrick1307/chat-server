from dataclasses import dataclass
from typing import TypeVar, Generic, Optional

T = TypeVar("T")


@dataclass(slots=True)
class BaseView:
    """Base class for view response objects."""
    pass


@dataclass(slots=True)
class PaginatedResponse(Generic[T]):
    """Generic paginated response wrapper."""
    items: list[T]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


@dataclass(slots=True)
class ApiResponse(Generic[T]):
    """Standard API response wrapper."""
    success: bool
    data: Optional[T] = None
    message: Optional[str] = None
    error: Optional[str] = None
