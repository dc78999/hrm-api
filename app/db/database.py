import os
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors as psycopg2_errors
from typing import List, Tuple, Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

def get_db():
    """Get PostgreSQL connection"""
    return psycopg2.connect(
        host="postgres-hrm",
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
    try:
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
    
    except psycopg2_errors.InvalidTextRepresentation as e:
        logger.error(f"Invalid text representation error in search_employees: {e}")
        logger.error(f"Query params: organization_id={organization_id}, q={q}, location={location}, position={position}, status={status}")
        raise ValueError(f"Invalid search parameters: {str(e)}")
    
    except psycopg2_errors.UndefinedColumn as e:
        logger.error(f"Undefined column error in search_employees: {e}")
        raise ValueError(f"Database schema error: {str(e)}")
    
    except psycopg2_errors.SyntaxError as e:
        logger.error(f"SQL syntax error in search_employees: {e}")
        raise ValueError(f"Invalid search query syntax: {str(e)}")
    
    except psycopg2_errors.DataError as e:
        logger.error(f"Data error in search_employees: {e}")
        raise ValueError(f"Invalid data format in search parameters: {str(e)}")
    
    except psycopg2.OperationalError as e:
        logger.error(f"Database operational error in search_employees: {e}")
        raise ConnectionError(f"Database connection error: {str(e)}")
    
    except psycopg2.DatabaseError as e:
        logger.error(f"Database error in search_employees: {e}")
        raise RuntimeError(f"Database error occurred: {str(e)}")
    
    except Exception as e:
        logger.error(f"Unexpected error in search_employees: {e}")
        logger.error(f"Error type: {type(e)}")
        raise RuntimeError(f"Unexpected error during employee search: {str(e)}")
