"""
Enterprise Response Builder - Complete Architecture Implementation
=================================================================
Full enterprise response system with builders, utilities, and middleware.
This file extends the basic response.py with comprehensive functionality.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Generic, TypeVar
from pydantic import BaseModel, Field
import uuid

from .response import (
    BaseApiResponse, ListApiResponse, ResponseStatus, ErrorType, 
    ErrorDetail, PaginationInfo, ResponseMetadata
)

T = TypeVar('T')

class ResponseBuilder:
    """Builder pattern for creating standardized API responses"""
    
    def __init__(self):
        self._status = ResponseStatus.SUCCESS
        self._message = "Operation completed successfully"
        self._data = None
        self._errors = []
        self._metadata = ResponseMetadata()
        self._start_time = datetime.utcnow()
    
    def success(self, message: str = "Operation completed successfully") -> 'ResponseBuilder':
        """Set successful response status"""
        self._status = ResponseStatus.SUCCESS
        self._message = message
        return self
    
    def error(self, message: str = "Operation failed") -> 'ResponseBuilder':
        """Set error response status"""
        self._status = ResponseStatus.ERROR
        self._message = message
        return self
    
    def warning(self, message: str = "Operation completed with warnings") -> 'ResponseBuilder':
        """Set warning response status"""
        self._status = ResponseStatus.WARNING
        self._message = message
        return self
    
    def partial(self, message: str = "Operation partially completed") -> 'ResponseBuilder':
        """Set partial success response status"""
        self._status = ResponseStatus.PARTIAL
        self._message = message
        return self
    
    def data(self, data: Any) -> 'ResponseBuilder':
        """Set response data"""
        self._data = data
        return self
    
    def add_error(
        self,
        code: str,
        message: str,
        error_type: ErrorType,
        field: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> 'ResponseBuilder':
        """Add error detail to response"""
        error = ErrorDetail(
            code=code,
            message=message,
            type=error_type,
            field=field,
            details=details
        )
        self._errors.append(error)
        return self
    
    def add_validation_error(self, field: str, message: str, details: Optional[Dict[str, Any]] = None) -> 'ResponseBuilder':
        """Add validation error detail"""
        return self.add_error(
            code="VALIDATION_ERROR",
            message=message,
            error_type=ErrorType.VALIDATION_ERROR,
            field=field,
            details=details
        )
    
    def add_business_error(self, message: str, details: Optional[Dict[str, Any]] = None) -> 'ResponseBuilder':
        """Add business logic error detail"""
        return self.add_error(
            code="BUSINESS_ERROR",
            message=message,
            error_type=ErrorType.BUSINESS_ERROR,
            details=details
        )
    
    def with_correlation_id(self, correlation_id: str) -> 'ResponseBuilder':
        """Set correlation ID"""
        self._metadata.correlation_id = correlation_id
        return self
    
    def with_version(self, version: str) -> 'ResponseBuilder':
        """Set API version"""
        self._metadata.version = version
        return self
    
    def with_warning(self, warning: str) -> 'ResponseBuilder':
        """Add warning message"""
        if not self._metadata.warnings:
            self._metadata.warnings = []
        self._metadata.warnings.append(warning)
        return self
    
    def build(self) -> BaseApiResponse:
        """Build final response"""
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - self._start_time).total_seconds() * 1000
        self._metadata.execution_time_ms = round(execution_time, 2)
        
        # Create response
        response = BaseApiResponse(
            status=self._status,
            message=self._message,
            data=self._data,
            errors=self._errors if self._errors else None,
            metadata=self._metadata
        )
        
        return response

class ListResponseBuilder:
    """Builder for paginated list responses"""
    
    def __init__(self):
        self._status = ResponseStatus.SUCCESS
        self._message = "Items retrieved successfully"
        self._data = []
        self._errors = []
        self._metadata = ResponseMetadata()
        self._start_time = datetime.utcnow()
        self._pagination = None
    
    def success(self, message: str = "Items retrieved successfully") -> 'ListResponseBuilder':
        """Set successful response status"""
        self._status = ResponseStatus.SUCCESS
        self._message = message
        return self
    
    def data(self, items: List[Any], current_page: int, items_per_page: int, total_items: int) -> 'ListResponseBuilder':
        """Set list data with pagination"""
        self._data = items
        
        total_pages = (total_items + items_per_page - 1) // items_per_page
        self._pagination = PaginationInfo(
            current_page=current_page,
            total_pages=total_pages,
            total_items=total_items,
            items_per_page=items_per_page,
            has_next=current_page < total_pages,
            has_previous=current_page > 1
        )
        return self
    
    def add_error(self, error: ErrorDetail) -> 'ListResponseBuilder':
        """Add error detail"""
        self._errors.append(error)
        return self
    
    def build(self) -> ListApiResponse:
        """Build final list response"""
        # Calculate execution time
        end_time = datetime.utcnow()
        execution_time = (end_time - self._start_time).total_seconds() * 1000
        self._metadata.execution_time_ms = round(execution_time, 2)
        
        return ListApiResponse(
            status=self._status,
            message=self._message,
            data=self._data,
            pagination=self._pagination,
            errors=self._errors if self._errors else None,
            metadata=self._metadata
        )

# Utility functions for common response patterns
def create_success_response(data: Any = None, message: str = "Operation completed successfully") -> BaseApiResponse:
    """Create standard success response"""
    return ResponseBuilder().success(message).data(data).build()

def create_error_response(
    message: str = "Operation failed",
    errors: Optional[List[ErrorDetail]] = None,
    status: ResponseStatus = ResponseStatus.ERROR
) -> BaseApiResponse:
    """Create standard error response"""
    builder = ResponseBuilder().error(message)
    if errors:
        for error in errors:
            builder.add_error(error.code, error.message, error.type, error.field, error.details)
    return builder.build()

def create_validation_error_response(validation_errors: Dict[str, List[str]]) -> BaseApiResponse:
    """Create validation error response from field errors"""
    builder = ResponseBuilder().error("Validation failed")
    
    for field, messages in validation_errors.items():
        for message in messages:
            builder.add_validation_error(field, message)
    
    return builder.build()

def create_not_found_response(resource: str, identifier: str) -> BaseApiResponse:
    """Create not found error response"""
    return ResponseBuilder().error(f"{resource} not found").add_error(
        code="NOT_FOUND",
        message=f"{resource} with identifier '{identifier}' was not found",
        error_type=ErrorType.NOT_FOUND_ERROR,
        details={"resource": resource, "identifier": identifier}
    ).build()

def create_conflict_error_response(message: str, details: Optional[Dict[str, Any]] = None) -> BaseApiResponse:
    """Create conflict error response"""
    return ResponseBuilder().error(message).add_error(
        code="CONFLICT",
        message=message,
        error_type=ErrorType.CONFLICT_ERROR,
        details=details
    ).build()

def create_list_response(
    items: List[Any],
    current_page: int,
    items_per_page: int,
    total_items: int,
    message: str = "Items retrieved successfully"
) -> ListApiResponse:
    """Create paginated list response"""
    return ListResponseBuilder().success(message).data(
        items, current_page, items_per_page, total_items
    ).build()

# QC-specific response utilities
def create_qc_response(qc_data: Any, validation_result: str = "PASS") -> BaseApiResponse:
    """Create QC-specific response with validation result"""
    message = f"QC check completed with result: {validation_result}"
    
    if validation_result == "FAIL":
        return ResponseBuilder().error(message).data(qc_data).build()
    elif validation_result == "WARNING":
        return ResponseBuilder().warning(message).data(qc_data).build()
    else:
        return ResponseBuilder().success(message).data(qc_data).build()

def create_temperature_response(temperature_data: List[Dict[str, Any]], facility_id: str) -> BaseApiResponse:
    """Create temperature monitoring response"""
    # Analyze temperature readings for summary
    total_readings = len(temperature_data)
    alerts = sum(1 for reading in temperature_data if reading.get('validation_result') in ['FAIL', 'WARNING'])
    
    if total_readings == 0:
        return ResponseBuilder().warning("No temperature readings found").data(
            {"readings": temperature_data, "summary": {"total": 0, "alerts": 0}}
        ).build()
    
    if alerts > 0:
        return ResponseBuilder().warning(
            f"Temperature monitoring complete: {alerts} alerts detected"
        ).data({
            "readings": temperature_data,
            "summary": {"total": total_readings, "alerts": alerts},
            "facility_id": facility_id
        }).build()
    
    return ResponseBuilder().success(
        "Temperature monitoring complete: All readings within normal range"
    ).data({
        "readings": temperature_data,
        "summary": {"total": total_readings, "alerts": 0},
        "facility_id": facility_id
    }).build()

def create_batch_response(batch_data: Any, qc_status: str = "PENDING") -> BaseApiResponse:
    """Create batch-specific response with status"""
    message = f"Batch {batch_data.get('batch_number', 'unknown')} status: {qc_status}"
    
    if qc_status == "COMPLETED":
        return ResponseBuilder().success(message).data(batch_data).build()
    elif qc_status == "FAILED":
        return ResponseBuilder().error(message).data(batch_data).build()
    else:
        return ResponseBuilder().success(message).data(batch_data).build()

# Response middleware for Flask
class EnterpriseResponseMiddleware:
    """Middleware to automatically wrap Flask responses with enterprise format"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize Flask application with response middleware"""
        app.after_request(self._standardize_flask_response)
    
    def _standardize_flask_response(self, response):
        """Wrap Flask response with standard format if needed"""
        # This would be implemented to automatically wrap Flask responses
        # For now, just return the response as-is
        return response

# Response caching utilities
class ResponseCache:
    """Utilities for caching responses"""
    
    @staticmethod
    def get_cache_key(controller: str, action: str, params: Dict[str, Any]) -> str:
        """Generate cache key for response"""
        import hashlib
        param_str = str(sorted(params.items()))
        hash_obj = hashlib.md5(f"{controller}:{action}:{param_str}".encode())
        return f"response:{controller}:{action}:{hash_obj.hexdigest()[:8]}"
    
    @staticmethod
    def create_cacheable_response(data: Any, cache_key: str, ttl: int = 300) -> Dict[str, Any]:
        """Create cacheable response wrapper"""
        return {
            "data": data,
            "cache_key": cache_key,
            "cache_ttl": ttl,
            "cached_at": datetime.utcnow()
        }

# Response validation helpers
def validate_response_compliance(response: BaseApiResponse) -> Dict[str, Any]:
    """Validate response complies with enterprise standards"""
    validation_result = {
        "is_valid": True,
        "errors": [],
        "warnings": []
    }
    
    # Check required fields
    if not response.status:
        validation_result["errors"].append("Missing status field")
        validation_result["is_valid"] = False
    
    if not response.message:
        validation_result["errors"].append("Missing message field")
        validation_result["is_valid"] = False
    
    if not response.metadata:
        validation_result["errors"].append("Missing metadata field")
        validation_result["is_valid"] = False
    
    # Check error consistency
    if response.status == ResponseStatus.ERROR and not response.errors:
        validation_result["warnings"].append("Error status without error details")
    
    # Check metadata completeness
    if response.metadata and not response.metadata.request_id:
        validation_result["warnings"].append("Missing request ID in metadata")
    
    return validation_result