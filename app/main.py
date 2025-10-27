from contextlib import asynccontextmanager
from typing import Optional
import logging
from fastapi import FastAPI, Query, HTTPException, Header

from .models import SearchResponse
from .db.database import ensure_db, search_employees

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup Logic (Runs before the application starts accepting requests)
        
    yield # <-- Everything above 'yield' is startup logic.
    
    # 2. Shutdown Logic (Runs after the application stops accepting requests)
    print("Application shutdown: Performing cleanup...")
    # Add any cleanup tasks here, e.g., closing database connection pools or clearing caches.


app = FastAPI(
    title="hrm-api", 
    description="HRM API with dynamic columns and simple rate limiting",
    lifespan=lifespan # <-- Pass the new context manager here
)

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
    Requires organization_id in headers for data isolation.
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
