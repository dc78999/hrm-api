from contextlib import asynccontextmanager
from typing import Optional
import logging
import os
import time
from fastapi import FastAPI, Query, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import SearchResponse, ErrorResponse, RateLimitError, HealthResponse
from .db.database import ensure_db, search_employees
from .middleware.rate_limiter import RateLimitMiddleware

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Logic
    ensure_db()
    # Initialize rate limiter
    persistence_dir = os.getenv("RATE_LIMIT_STORAGE", "./data")
    logger.info(f"Initializing rate limiter with persistence directory: {persistence_dir}")
    
    yield
    
    # Shutdown Logic
    print("Application shutdown: Performing cleanup...")
    # Save rate limiter state on shutdown
    if hasattr(app.state, 'rate_limiter'):
        try:
            app.state.rate_limiter.limiter._save_to_file()
            logger.info("Rate limiter state saved on shutdown")
        except Exception as e:
            logger.error(f"Failed to save rate limiter state: {e}")

# Enhanced OpenAPI configuration
app = FastAPI(
    title="HRM Employee Search API",
    description="""
    ## Human Resources Management API

    A high-performance employee search system designed for HR applications managing millions of employee records.

    ### Features

    * **Advanced Search**: Full-text search across all employee fields with intelligent ranking
    * **Dynamic Columns**: Flexible JSONB-based data structure supporting organization-specific fields
    * **Multi-tenant Security**: Organization-level data isolation with Row Level Security
    * **Rate Limiting**: Built-in protection against API abuse (custom implementation)
    * **High Performance**: Optimized for millions of records with proper indexing strategies

    ### Getting Started

    1. **Authentication**: All endpoints require an `X-Organization-ID` header
    2. **Search**: Use the `/api/v1/employees/search` endpoint with various filters
    3. **Pagination**: Results are paginated (max 100 items per page)
    4. **Rate Limits**: Monitor the response headers for rate limit status

    ### Available Test Organization IDs

    You can use these organization UUIDs for testing:
    - `124690d3-458f-4ead-8c57-532a7cd6892b` (Primary test org - 500+ employees)
    - `68e529cc-78ba-4179-b955-76f1624550ae` (Secondary test org - 400+ employees)  
    - `feb99c04-3b47-413e-8387-959574862e24` (Test org - 300+ employees)

    ### Rate Limiting

    The API implements intelligent rate limiting:
    - **Search Endpoints**: 200 requests/hour, 20 requests/minute
    - **Health Endpoints**: 1000 requests/minute (very lenient)
    - **General API**: 1000 requests/hour, 100 requests/minute

    Rate limit information is provided in response headers:
    - `X-RateLimit-Limit`: Maximum requests allowed
    - `X-RateLimit-Remaining`: Requests remaining in current window
    - `X-RateLimit-Reset`: Unix timestamp when limit resets

    ### Example Usage

    ```bash
    # Basic search
    curl -X GET "http://localhost:8000/api/v1/employees/search" \\
         -H "X-Organization-ID: 124690d3-458f-4ead-8c57-532a7cd6892b"

    # Advanced search with filters
    curl -X GET "http://localhost:8000/api/v1/employees/search?q=engineer&location=Engineering&status=active&page=1&page_size=20" \\
         -H "X-Organization-ID: 124690d3-458f-4ead-8c57-532a7cd6892b"
    ```
    """,
    version="1.0.0",
    terms_of_service="https://example.com/terms/",
    contact={
        "name": "API Support Team",
        "url": "https://example.com/contact/",
        "email": "api-support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        },
        {
            "url": "https://api-staging.example.com",
            "description": "Staging server"
        },
        {
            "url": "https://api.example.com", 
            "description": "Production server"
        }
    ],
    openapi_tags=[
        {
            "name": "employees",
            "description": "Employee search and management operations. The core functionality for searching through employee records.",
        },
        {
            "name": "health",
            "description": "System health monitoring and diagnostics. Use these endpoints to monitor API status and performance.",
        },
    ],
    lifespan=lifespan
)

# Add CORS middleware (if needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize and add rate limiting middleware
persistence_dir = os.getenv("RATE_LIMIT_STORAGE", "./data")
rate_limiter = RateLimitMiddleware(persistence_dir=persistence_dir)

# Store rate limiter in app state for access in lifespan
app.state.rate_limiter = rate_limiter

# Add the rate limiting middleware
app.middleware("http")(rate_limiter)

@app.get(
    "/health",
    tags=["health"],
    summary="Health Check",
    description="Check the health status of the API service",
    response_model=HealthResponse,
    responses={
        200: {
            "description": "Service is healthy and operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "service": "hrm-api", 
                        "timestamp": 1703097600
                    }
                }
            }
        }
    }
)
async def health_check():
    """
    Perform a basic health check on the API service.
    
    This endpoint:
    - Confirms the API is running and responsive
    - Returns current timestamp for debugging
    - Has lenient rate limiting for monitoring tools
    
    Used by:
    - Load balancers for health checks
    - Monitoring systems (Prometheus, Datadog, etc.)
    - DevOps teams for service verification
    """
    return {"status": "healthy", "service": "hrm-api", "timestamp": int(time.time())}

@app.get(
    "/health/rate-limit-stats", 
    tags=["health"],
    summary="Rate Limit Statistics",
    description="Get detailed statistics about the rate limiting system"
)
async def rate_limit_stats():
    """
    Retrieve comprehensive rate limiting statistics and configuration.
    
    Returns:
    - Active rate limiting rules and their thresholds
    - Current system statistics (total keys, entries, cleanup info)
    - Rule-specific metrics for monitoring
    
    Useful for:
    - Monitoring API usage patterns  
    - Debugging rate limit issues
    - Capacity planning and optimization
    """
    return rate_limiter.get_stats()

@app.get(
    "/api/v1/employees/search", 
    response_model=SearchResponse,
    tags=["employees"],
    summary="Search Employees",
    description="Search employees with advanced filtering, full-text search, and pagination",
    responses={
        200: {
            "description": "Successfully retrieved employee search results",
            "model": SearchResponse,
        },
        422: {
            "description": "Validation error - invalid request parameters",
            "model": ErrorResponse,
            "content": {
                "application/json": {
                    "example": {
                        "error": "validation_error",
                        "message": "Invalid request parameters",
                        "detail": [
                            {
                                "loc": ["query", "page_size"],
                                "msg": "ensure this value is less than or equal to 100", 
                                "type": "value_error.number.not_le"
                            }
                        ]
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded - too many requests",
            "model": RateLimitError,
            "content": {
                "application/json": {
                    "example": {
                        "error": "Rate limit exceeded",
                        "message": "Too many requests. Limit: 200 requests per hour.",
                        "rule": "search_detailed",
                        "retry_after": 3600,
                        "reset_time": 1703097660
                    }
                }
            }
        },
        500: {
            "description": "Internal server error",
            "model": ErrorResponse
        }
    }
)
async def search_employees_endpoint(
    x_organization_id: str = Header(
        ..., 
        alias="X-Organization-ID",
        description="🏢 **Organization UUID** for multi-tenant data access. Required for security and data isolation.",
        example="124690d3-458f-4ead-8c57-532a7cd6892b"
    ),
    q: Optional[str] = Query(
        None, 
        description="🔍 **Full-text search query**. Searches across names, emails, positions, departments, and other text fields. Case-insensitive with intelligent ranking.",
        example="Engineering Python developer",
        max_length=500
    ),
    location: Optional[str] = Query(
        None, 
        description="📍 **Filter by work location**. Exact match (case-insensitive). Based on actual data: Engineering, Marketing, Finance, HR, Product, Sales.",
        example="Engineering",
        max_length=100
    ),
    position: Optional[str] = Query(
        None, 
        description="💼 **Filter by job position/title**. Exact match (case-insensitive). Based on actual data: Engineering, Marketing, Finance, HR, Product, Sales.",
        example="Engineering",
        max_length=100
    ),
    department: Optional[str] = Query(
        None, 
        description="🏢 **Filter by department**. Exact match (case-insensitive) from employee data. Based on actual data: Engineering, Marketing, Finance, HR, Product, Sales.",
        example="Engineering",
        max_length=100
    ),
    status: Optional[str] = Query(
        None, 
        description="📊 **Filter by employment status**. Valid values: `active`, `inactive`, `terminated`",
        example="active",
        regex="^(active|inactive|terminated)$"
    ),
    page: int = Query(
        1, 
        ge=1, 
        description="📄 **Page number** for pagination (1-based indexing). Must be positive integer.",
        example=1
    ),
    page_size: int = Query(
        10, 
        ge=1, 
        le=100, 
        description="📏 **Items per page**. Maximum 100 items to prevent performance issues.",
        example=20
    )
):
    """
    ## 🚀 Advanced Employee Search
    
    Search through employee records with powerful filtering and full-text search capabilities.
    
    ### 🔍 Search Features
    
    **Full-Text Search (`q` parameter):**
    - Searches across employee names, emails, phone numbers, departments, and custom fields
    - Supports partial matches and multiple keywords  
    - Results are ranked by relevance
    - Case-insensitive matching
    
    **🎯 Exact Filters:**
    - `location`: Work office/location (Engineering, Marketing, Finance, HR, Product, Sales)
    - `position`: Job title/role (Engineering, Marketing, Finance, HR, Product, Sales) 
    - `department`: Employee department (Engineering, Marketing, Finance, HR, Product, Sales)
    - `status`: Employment status (active, inactive, terminated)
    
    **📄 Pagination:**
    - Use `page` and `page_size` to control result sets
    - Maximum 100 items per page to ensure performance
    - Total count provided in response for UI pagination
    
    ### ⚡ Performance Notes
    
    - Queries are optimized with GIN indexes for fast full-text search
    - Department field is indexed with high priority (weight 'A') for fast department searches
    - JSONB fields are efficiently searchable
    - Database connection pooling ensures consistent performance
    - Rate limiting prevents system overload
    
    ### 🔒 Security & Data Isolation
    
    - Organization-level data isolation via Row Level Security (RLS)
    - Only employees from the specified organization are returned
    - No cross-organization data leakage possible
    
    ### 📖 Real Example Searches
    
    **Find employees in Engineering department:**
    ```bash
    GET /api/v1/employees/search?department=Engineering
    ```
    
    **Find Finance department employees with Leadership skills:**  
    ```bash
    GET /api/v1/employees/search?department=Finance&q=Leadership
    ```
    
    **Search for Python developers in specific department:**
    ```bash
    GET /api/v1/employees/search?department=Engineering&q=Python
    ```
    
    **Find Marketing department employees at specific location:**
    ```bash
    GET /api/v1/employees/search?department=Marketing&location=Marketing
    ```
    
    **Complex search - HR department with Communication skills:**
    ```bash
    GET /api/v1/employees/search?department=HR&q=Communication&status=active&page=1&page_size=20
    ```
    
    ### 💡 Tips for Department Search
    
    - Use the **Try it out** button below to test department searches interactively
    - Try searching for department names: "Engineering", "Marketing", "Finance", "HR", "Product", "Sales"
    - Combine department filter with skills search: department=Engineering&q=Python
    - Department filter works with all other filters and pagination
    """
    logger.info(f"Searching employees for organization: {x_organization_id}")
    logger.info(f"Search params: q={q}, location={location}, position={position}, department={department}, status={status}")
    logger.info(f"Pagination: page={page}, page_size={page_size}")
    
    # Validate pagination parameters
    if page < 1:
        raise HTTPException(status_code=422, detail="Page number must be greater than 0")
    if page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Page size must be between 1 and 100")
    
    try:
        result = search_employees(
            organization_id=x_organization_id,
            q=q,
            location=location,
            position=position,
            department=department,  # Add department parameter
            status=status,
            page=page,
            page_size=page_size
        )
        logger.info(f"Search returned {len(result['items'])} items out of {result['total']} total")
        return result
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=422, detail=str(e))
    except ConnectionError as e:
        logger.error(f"Database connection error: {str(e)}")
        raise HTTPException(status_code=503, detail="Database connection error")
    except Exception as e:
        logger.error(f"Search failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

# Custom exception handlers for better OpenAPI documentation
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=f"http_error_{exc.status_code}",
            message=str(exc.detail),
            detail=exc.detail if isinstance(exc.detail, (dict, list)) else None
        ).model_dump()
    )

@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    """Handle validation errors with consistent format"""
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            message=str(exc),
            detail=str(exc)
        ).model_dump()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle unexpected errors with consistent format"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="An unexpected error occurred",
            detail=str(exc) if os.getenv("DEBUG") else None
        ).model_dump()
    )

# Customize OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add custom security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "OrganizationHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Organization-ID",
            "description": "Organization UUID for multi-tenant access control"
        }
    }
    
    # Apply security to search endpoints
    for path, path_item in openapi_schema["paths"].items():
        if path.startswith("/api/"):
            for method in path_item:
                if method in ["get", "post", "put", "delete", "patch"]:
                    path_item[method]["security"] = [{"OrganizationHeader": []}]
    
    # Add rate limiting headers to responses
    rate_limit_headers = {
        "X-RateLimit-Limit": {
            "description": "Request limit for the current window",
            "schema": {"type": "string"}
        },
        "X-RateLimit-Remaining": {
            "description": "Remaining requests in current window", 
            "schema": {"type": "string"}
        },
        "X-RateLimit-Reset": {
            "description": "Unix timestamp when the limit resets",
            "schema": {"type": "string"}
        },
        "X-RateLimit-Rule": {
            "description": "Which rate limiting rule was applied",
            "schema": {"type": "string"}
        }
    }
    
    # Add rate limit headers to successful responses
    for path, path_item in openapi_schema["paths"].items():
        for method in path_item:
            if method in ["get", "post", "put", "delete", "patch"]:
                responses = path_item[method].get("responses", {})
                for status_code in ["200", "201"]:
                    if status_code in responses:
                        if "headers" not in responses[status_code]:
                            responses[status_code]["headers"] = {}
                        responses[status_code]["headers"].update(rate_limit_headers)
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
