from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Query, HTTPException, Header
from .db.database import ensure_db
from .models import SearchResponse

app = FastAPI(title="hrm-api", description="HRM API with dynamic columns and simple rate limiting")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup Logic (Runs before the application starts accepting requests)
    print("Application startup: Ensuring database connection is ready...")
    ensure_db()
    
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
async def search_employees(
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
    raise HTTPException(status_code=501, detail="Not implemented")
