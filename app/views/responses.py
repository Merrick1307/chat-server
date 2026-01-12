"""
Standard API response classes with orjson serialization support.

All API endpoints should return one of these response types for consistency:
- APIResponse: Standard success/error wrapper
- PaginatedResponse: For list endpoints with pagination
- ErrorResponse: For error conditions
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, List, Optional

import orjson
from starlette.responses import JSONResponse


class OrjsonResponse(JSONResponse):
    """High-performance JSON response using orjson with native dataclass support."""
    media_type = "application/json"
    
    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z | orjson.OPT_SERIALIZE_DATACLASS
        )


def _now() -> str:
    """Generate current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class APIResponse:
    """Standard API response wrapper.
    
    Usage:
        return APIResponse(data=user_data, message="User created")
        return APIResponse(success=False, message="Validation failed")
    """
    success: bool = True
    data: Any = None
    message: Optional[str] = None
    timestamp: str = field(default_factory=_now)


@dataclass(slots=True)
class PaginationMeta:
    """Pagination metadata for list responses."""
    page: int = 1
    page_size: int = 20
    total_items: int = 0
    total_pages: int = 0
    
    @classmethod
    def create(cls, page: int, page_size: int, total_items: int) -> "PaginationMeta":
        """Factory method to calculate pagination from raw values."""
        total_pages = (total_items + page_size - 1) // page_size if page_size > 0 else 0
        return cls(page=page, page_size=page_size, total_items=total_items, total_pages=total_pages)


@dataclass(slots=True)
class PaginatedResponse:
    """Paginated list response for collection endpoints.
    
    Usage:
        return PaginatedResponse(
            data=messages,
            pagination=PaginationMeta.create(page=1, page_size=20, total_items=100)
        )
    """
    data: List[Any] = field(default_factory=list)
    pagination: PaginationMeta = field(default_factory=PaginationMeta)
    success: bool = True
    timestamp: str = field(default_factory=_now)


@dataclass(slots=True)
class ErrorDetail:
    """Individual field-level error detail."""
    code: str
    message: str
    field: Optional[str] = None


@dataclass(slots=True)
class ErrorBody:
    """Structured error information."""
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None
    path: Optional[str] = None
    method: Optional[str] = None


@dataclass(slots=True)
class ErrorResponse:
    """Standard error response wrapper.
    
    Usage:
        return ErrorResponse(
            error=ErrorBody(code="VALIDATION_ERROR", message="Invalid input")
        )
    """
    error: ErrorBody
    success: bool = False
    timestamp: str = field(default_factory=_now)
