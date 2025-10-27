from contextlib import asynccontextmanager
from typing import Optional
import logging
import os
import time
from fastapi import FastAPI, Query, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware

from .models import SearchResponse
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

app = FastAPI(
    title="hrm-api", 
    description="HRM API with dynamic columns and in-memory rate limiting",
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

@app.get("/health")
async def health_check():
    """Health check endpoint (has its own rate limiting rules)"""
    # TODO: implement logic to check 
    return {"status": "healthy", "service": "hrm-api", "timestamp": int(time.time())}

@app.get("/health/rate-limit-stats")
async def rate_limit_stats():
    """Get rate limiter statistics (for monitoring)"""
    return rate_limiter.get_stats()

@app.get("/api/v1/employees/search", response_model=SearchResponse)
async def search_employees_endpoint(
    x_organization_id: str = Header(..., alias="X-Organization-ID"),
    q: Optional[str] = Query(None, description="Search query across all fields"),
    location: Optional[str] = Query(None, description="Filter by location"),
    position: Optional[str] = Query(None, description="Filter by position"),
    status: Optional[str] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page")
):
    """
    Search employees with filters and full-text search.
    Rate limited: 200 requests/hour, 20 requests/minute per client.
    """
    logger.info(f"Searching employees for organization: {x_organization_id}")
    logger.info(f"Search params: q={q}, location={location}, position={position}, status={status}")
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
