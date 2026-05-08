"""
Standardized API Response - Enterprise Architecture
=================================================
Unified API response format for all endpoints supporting:
- Consistent structure across all responses
- Error handling with proper HTTP status codes
- Pagination support
- Metadata and correlation tracking
- Version compatibility
- Performance metrics

Follows REST API best practices and OpenAPI standards.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from pydantic import BaseModel, Field
from enum import Enum
import uuid

T = TypeVar('T')

class ResponseStatus(str, Enum):
    """Standard response status codes"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    PARTIAL = "partial"

class ErrorType(str, Enum):
    """Categorized error types for client handling"""
    VALIDATION_ERROR = "validation_error"
    BUSINESS_ERROR = "business_error"
    SYSTEM_ERROR = "system_error"
    AUTHENTICATION_ERROR = "authentication_error"
    AUTHORIZATION_ERROR = "authorization_error"
    NOT_FOUND_ERROR = "not_found_error"
    CONFLICT_ERROR = "conflict_error"
    RATE_LIMIT_ERROR = "rate_limit_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"

class ErrorDetail(BaseModel):
    """Detailed error information"""
    
    code: str = Field(..., description="Error code for client handling")
    message: str = Field(..., description="Human-readable error message")
    type: ErrorType = Field(..., description="Category of error")
    field: Optional[str] = Field(None, description="Field that caused validation error")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error context")
    
    class Config:
        use_enum_values = True

class PaginationInfo(BaseModel):
    """Pagination metadata for list responses"""
    
    current_page: int = Field(..., ge=1, description="Current page number")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    total_items: int = Field(..., ge=0, description="Total number of items")
    items_per_page: int = Field(..., ge=1, le=100, description="Items per page")
    has_next: bool = Field(..., description="Next page available")
    has_previous: bool = Field(..., description="Previous page available")

class ResponseMetadata(BaseModel):
    """Response metadata for tracking and debugging"""
    
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique request ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    version: str = Field(default="v1", description="API version")
    execution_time_ms: Optional[float] = Field(None, description="Execution time in milliseconds")
    server_instance: Optional[str] = Field(None, description="Server instance identifier")
    correlation_id: Optional[str] = Field(None, description="Correlation ID for distributed tracing")
    warnings: Optional[List[str]] = Field(None, description="Warning messages")
    
    class Config:
        extra = "allow"  # Allow additional metadata fields

class BaseApiResponse(BaseModel, Generic[T]):
    """Base API response with common structure"""
    
    status: ResponseStatus = Field(..., description="Overall response status")
    message: str = Field(..., description="Response message")
    data: Optional[T] = Field(None, description="Response payload")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Error details if any")
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata, description="Response metadata")
    
    class Config:
        use_enum_values = True
        extra = "ignore"

class ListApiResponse(BaseModel, Generic[T]):
    """List response with pagination support"""
    
    status: ResponseStatus = Field(..., description="Overall response status")
    message: str = Field(..., description="Response message")
    data: List[T] = Field(..., description="List of items")
    pagination: PaginationInfo = Field(..., description="Pagination information")
    errors: Optional[List[ErrorDetail]] = Field(None, description="Error details if any")
    metadata: ResponseMetadata = Field(default_factory=ResponseMetadata, description="Response metadata")
    
    class Config:
        use_enum_values = True

# Backward compatibility functions
def success(data: Any = None, message: str = "OK", status_code: int = 200) -> Dict[str, Any]:
    """Legacy success function - creates standard response"""
    from .enterprise_response import ResponseBuilder
    response = ResponseBuilder().success(message or "Operation completed successfully").data(data).build()
    return response.dict()

def error(message: str = "Error", code: int = 500, details: Optional[Any] = None) -> Dict[str, Any]:
    """Legacy error function - creates standard error response"""
    from .enterprise_response import ResponseBuilder, ErrorType
    builder = ResponseBuilder().error(message)
    
    if details:
        builder.add_error("ERROR", str(details), ErrorType.SYSTEM_ERROR)
    
    response = builder.build()
    return response.dict()

def paginated(items: Any, total: int, page: int = 1, per_page: int = 25) -> Dict[str, Any]:
    """Legacy paginated function - creates standard list response"""
    from .enterprise_response import ListResponseBuilder
    response = ListResponseBuilder().success("Items retrieved successfully").data(
        items, page, per_page, total
    ).build()
    return response.dict()
