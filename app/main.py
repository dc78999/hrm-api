import json
import os
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, Query, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from .db import ensure_db, query_users
from .ratelimit import RateLimiter

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(os.path.dirname(BASE_DIR), "config", "columns.json")

app = FastAPI(title="hrm-api", description="HRM API with dynamic columns and simple rate limiting")
rate_limiter = RateLimiter(capacity=30, refill_rate_per_sec=0.5)  # small default limits for demo

def load_org_config() -> Dict[str, List[str]]:
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

ORG_CONFIG = load_org_config()

@app.on_event("startup")
def startup_event():
    ensure_db()

def get_client_key(request: Request) -> str:
    # Prefer X-API-Key if present, otherwise fallback to client host.
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return f"key:{api_key}"
    client = request.client.host if request.client else "unknown"
    return f"ip:{client}"

async def check_rate_limit(request: Request):
    key = get_client_key(request)
    allowed = rate_limiter.allow_request(key)
    if not allowed:
        raise HTTPException(status_code=429, detail="rate limit exceeded")

@app.get("/users", dependencies=[Depends(check_rate_limit)])
def list_users(
    org_id: str = Query(..., description="Organization identifier"),
    columns: Optional[str] = Query(None, description="Comma-separated list of columns to return"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000)
):
    """
    List users for an organization with dynamic columns and pagination.
    - The allowed columns/order for each organization are defined in config/columns.json
    - The 'columns' query param must be a subset (and ordered subset) of the org's allowed columns.
    """
    if org_id not in ORG_CONFIG:
        raise HTTPException(status_code=404, detail="organization not found")
    allowed_cols = ORG_CONFIG[org_id]

    if columns:
        requested = [c.strip() for c in columns.split(",") if c.strip()]
        # Enforce subset and ordering: requested must be within allowed_cols
        for c in requested:
            if c not in allowed_cols:
                raise HTTPException(status_code=400, detail=f"column '{c}' not allowed for this organization")
        use_cols = requested
    else:
        use_cols = allowed_cols

    limit = page_size
    offset = (page - 1) * page_size

    try:
        cols, rows = query_users(org_id=org_id, columns=use_cols, limit=limit, offset=offset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = [dict(zip(cols, row)) for row in rows]
    return {"org_id": org_id, "page": page, "page_size": page_size, "columns": cols, "data": result}
