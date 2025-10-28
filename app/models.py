from pydantic import BaseModel, UUID4, EmailStr, Field, ConfigDict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid

class EmployeeStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    TERMINATED = "terminated"

class EmployeeData(BaseModel):
    """Dynamic employee data stored in JSONB field with flexible schema"""
    model_config = ConfigDict(
        extra="allow",  # Allow additional fields for organization-specific customization
        json_schema_extra={
            "example": {
                "full_name": "Jason Noble",
                "email": "gtorres@example.net",
                "phone": "459-617-1404",
                "department": "Finance",
                "hire_date": "1983-04-17",
                "salary": 78926.22,
                "skills": ["Java", "Python", "SQL", "JavaScript"]
            }
        }
    )

class EmployeeResponse(BaseModel):
    """Complete employee record as returned by the API"""
    id: uuid.UUID = Field(..., description="Unique employee identifier (UUID)")
    organization_id: uuid.UUID = Field(..., description="Organization this employee belongs to") 
    location: str = Field(..., description="Employee work location/office")
    position: str = Field(..., description="Job position/title")
    status: str = Field(..., description="Employment status (active, inactive, terminated)")
    data: Dict[str, Any] = Field(..., description="Dynamic employee data (names, contact info, custom fields)")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Last modification timestamp")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "organization_id": "feb99c04-3b47-413e-8387-959574862e24",
                "location": "Finance",
                "position": "Finance", 
                "status": "active",
                "data": {
                    "full_name": "Jason Noble",
                    "email": "gtorres@example.net",
                    "phone": "459-617-1404",
                    "department": "Finance",
                    "hire_date": "1983-04-17",
                    "salary": 78926.22,
                    "skills": ["Java", "Python", "SQL", "JavaScript"]
                },
                "created_at": "1983-04-17T10:30:00Z",
                "updated_at": "2023-12-01T14:22:00Z"
            }
        }
    )

class SearchResponse(BaseModel):
    """Paginated search results for employee queries"""
    items: List[EmployeeResponse] = Field(..., description="List of employees matching the search criteria")
    total: int = Field(..., description="Total number of employees matching the search (across all pages)")
    page: int = Field(..., description="Current page number (1-based)")
    page_size: int = Field(..., description="Number of items requested per page")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "organization_id": "124690d3-458f-4ead-8c57-532a7cd6892b",
                        "location": "Engineering",
                        "position": "Engineering",
                        "status": "active", 
                        "data": {
                            "full_name": "Aaron Mcguire",
                            "email": "christinerice@example.net",
                            "phone": "001-608-614-5664x7490",
                            "department": "Engineering",
                            "hire_date": "2014-01-02",
                            "salary": 64658.05,
                            "skills": ["Communication", "Java"]
                        },
                        "created_at": "2014-01-02T10:30:00Z",
                        "updated_at": "2023-12-01T14:22:00Z"
                    },
                    {
                        "id": "550e8400-e29b-41d4-a716-446655440001",
                        "organization_id": "124690d3-458f-4ead-8c57-532a7cd6892b",
                        "location": "Marketing",
                        "position": "Marketing",
                        "status": "active", 
                        "data": {
                            "full_name": "Eileen Decker",
                            "email": "jessemanning@example.net",
                            "phone": "064.331.3760",
                            "department": "Marketing",
                            "hire_date": "1994-03-30",
                            "salary": 106440.55,
                            "skills": ["Python", "Leadership"]
                        },
                        "created_at": "1994-03-30T10:30:00Z",
                        "updated_at": "2023-12-01T14:22:00Z"
                    }
                ],
                "total": 500,
                "page": 1, 
                "page_size": 20
            }
        }
    )

class ErrorResponse(BaseModel):
    """Standard error response format for all API errors"""
    error: str = Field(..., description="Error type/category for programmatic handling")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[Any] = Field(None, description="Additional error details (validation errors, stack traces, etc.)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "validation_error",
                "message": "Request validation failed",
                "detail": [
                    {
                        "loc": ["query", "page_size"],
                        "msg": "ensure this value is less than or equal to 100",
                        "type": "value_error.number.not_le"
                    }
                ]
            }
        }
    )

class RateLimitError(BaseModel):
    """Rate limiting error response with retry information"""
    error: str = Field("Rate limit exceeded", description="Error type")
    message: str = Field(..., description="Descriptive error message with limit details")
    rule: str = Field(..., description="Which rate limiting rule was violated")
    retry_after: Optional[int] = Field(None, description="Seconds to wait before retrying")
    reset_time: int = Field(..., description="Unix timestamp when the rate limit resets")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": "Rate limit exceeded",
                "message": "Too many requests. Limit: 200 requests per hour.",
                "rule": "search_detailed", 
                "retry_after": 3600,
                "reset_time": 1703097660
            }
        }
    )

class HealthResponse(BaseModel):
    """Health check response indicating service status"""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name/identifier") 
    timestamp: int = Field(..., description="Current server timestamp (Unix time)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "healthy", 
                "service": "hrm-api",
                "timestamp": 1703097600
            }
        }
    )

class RateLimitStats(BaseModel):
    """Rate limiter statistics model"""
    limiter: Dict[str, Any] = Field(..., description="Rate limiter internal statistics")
    rules: Dict[str, Dict[str, int]] = Field(..., description="Configured rate limiting rules")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "limiter": {
                    "total_keys": 42,
                    "total_entries": 156,
                    "cleanup_interval": 300,
                    "last_cleanup": 1703097600
                },
                "rules": {
                    "api_general": {"max_requests": 10000, "window_seconds": 3600},
                    "api_burst": {"max_requests": 1000, "window_seconds": 60}
                }
            }
        }
    )

# Legacy models for backward compatibility
class Employee(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    department: str
    position: str
    location: str
    status: EmployeeStatus
    company: str
