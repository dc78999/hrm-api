import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import List, Tuple, Any, Dict, Optional

def get_db():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host="localhost",
        database="hrm_db",
        user="hrm_user",
        password="hrm_password"
    )

def ensure_db():
    """Verify database connection"""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1")

def query_users(org_id: str, columns: List[str], limit: int, offset: int) -> Tuple[List[str], List[Tuple[Any, ...]]]:
    """Query users with organization isolation"""
    if not columns:
        raise ValueError("no columns requested")
    
    # Implement the actual query logic here
    raise NotImplementedError("Query implementation pending")

def search_employees(
    organization_id: str,
    q: Optional[str] = None,
    location: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[str] = None,
    page: int = 1,
    page_size: int = 10
) -> Dict:
    """
    Search employees with pagination and filters.
    Returns exactly page_size items unless there aren't enough records.
    """
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            conditions = ["organization_id = %s"]
            params = [organization_id]

            if location:
                conditions.append("location = %s")
                params.append(location)
            if position:
                conditions.append("position = %s")
                params.append(position)
            if status:
                conditions.append("status = %s")
                params.append(status)
            if q:
                conditions.append("search_vector @@ plainto_tsquery('english', %s)")
                params.append(q)

            # Get paginated results first
            offset = (page - 1) * page_size
            sql = f"""
                SELECT id, organization_id, location, position, status, data, 
                       created_at, updated_at
                FROM employees 
                WHERE {" AND ".join(conditions)}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """
            cur.execute(sql, params + [page_size, offset])
            items = [dict(row) for row in cur.fetchall()]  # Convert to dict for serialization
            
            # Then get total count
            count_sql = f"SELECT COUNT(*) FROM employees WHERE {' AND '.join(conditions)}"
            cur.execute(count_sql, params)
            total = cur.fetchone()['count']

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size
            }
