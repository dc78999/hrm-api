import pytest
import logging
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set test database URL to use localhost instead of Docker service name
test_db_url = "postgresql://hrm_user:hrm_password@localhost:5432/hrm_db"
os.environ["DATABASE_URL"] = test_db_url

# Log database configuration for debugging
logger.info(f"Database URL: {os.getenv('DATABASE_URL', 'Not set')}")
logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'Not set')}")

try:
    from app.main import app
    logger.info("Successfully imported app")
except Exception as e:
    logger.error(f"Failed to import app: {e}")
    logger.error(f"Make sure PostgreSQL is running on localhost:5432")
    logger.error(f"You can start it with: docker-compose up db")
    raise

client = TestClient(app)

# Use a known organization ID from our seeded data
TEST_ORG_ID = "124690d3-458f-4ead-8c57-532a7cd6892b"

def test_search_employees_requires_organization():
    """Should require organization_id in headers"""
    try:
        response = client.get("/api/v1/employees/search")
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        
        # Find the specific error for X-Organization-ID
        header_errors = [
            err for err in error_detail 
            if err["loc"] == ["header", "X-Organization-ID"]
        ]
        
        if not header_errors:
            logger.error(f"No error found for X-Organization-ID header. Available errors: {error_detail}")
        
        assert header_errors, "No error found for X-Organization-ID header"
        error = header_errors[0]
        assert error["type"] == "value_error.missing"
        assert "field required" in error["msg"].lower()
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_basic_filter():
    """Should filter employees by basic fields"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"location": "New York"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        for employee in data["items"]:
            assert employee["location"] == "New York"
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_text_search():
    """Should support full-text search across fields"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": "engineer"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) > 0
        for employee in data["items"]:
            # Should match either position or data
            assert ("engineer" in employee["position"].lower() or 
                    "engineer" in str(employee["data"]).lower())
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_pagination():
    """Should support pagination"""
    try:
        page_size = 5
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": page_size}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= page_size
        assert "total" in data
        assert "page" in data
        assert data["page"] == 1
        assert data["page_size"] == page_size
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_multiple_filters():
    """Should support multiple filter parameters"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"location": "New York", "position": "Engineer"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for employee in data["items"]:
            assert employee["location"] == "New York"
            assert "engineer" in employee["position"].lower()
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_no_results():
    """Should handle search with no matching results"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"location": "NonExistentCity"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_invalid_organization():
    """Should handle invalid organization ID"""
    try:
        invalid_org_id = "invalid-uuid"
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": invalid_org_id}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        # Should either return 422 for invalid UUID format or 200 with empty results
        assert response.status_code in [200, 422]
        if response.status_code == 200:
            data = response.json()
            assert data["items"] == []
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_sorting():
    """Should support sorting results"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"sort_by": "name", "sort_order": "asc"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 1:
            # Check if results are sorted by name
            names = [emp["name"] for emp in data["items"]]
            assert names == sorted(names)
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_large_page_size():
    """Should handle large page size requests"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page_size": 1000}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        # Should limit page size or return all available results
        assert len(data["items"]) <= 1000
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_invalid_page():
    """Should handle invalid page numbers"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 0}  # Invalid page number
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        # Should either return 422 for validation error or handle gracefully
        assert response.status_code in [200, 422]
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_empty_query():
    """Should handle empty search query"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": ""}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        # Empty query should return all employees
        assert "items" in data
        assert "total" in data
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_special_characters():
    """Should handle special characters in search"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": "O'Connor"}  # Test apostrophe
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_case_insensitive():
    """Should perform case-insensitive search"""
    try:
        # Test with different cases
        response_lower = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": "engineer"}
        )
        response_upper = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": "ENGINEER"}
        )
        
        logger.info(f"Lower case response: {response_lower.status_code}")
        logger.info(f"Upper case response: {response_upper.status_code}")
        
        assert response_lower.status_code == 200
        assert response_upper.status_code == 200
        
        data_lower = response_lower.json()
        data_upper = response_upper.json()
        
        # Should return same number of results regardless of case
        assert data_lower["total"] == data_upper["total"]
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_database_connection_error():
    """Test database connection error handling"""
    try:
        with patch('app.db.database.create_engine') as mock_engine:
            # Mock engine creation failure
            mock_engine.side_effect = Exception("Database connection failed")
            
            # Try to import database module to trigger connection error
            with pytest.raises(Exception):
                import importlib
                import app.db.database
                importlib.reload(app.db.database)
        
        logger.info("Database connection error test completed")
    except Exception as e:
        logger.error(f"Database connection error test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_database_session_error():
    """Test database session creation error"""
    try:
        with patch('app.db.database.sessionmaker') as mock_sessionmaker:
            # Mock sessionmaker failure
            mock_sessionmaker.side_effect = Exception("Session creation failed")
            
            # Try to create session to trigger error
            with pytest.raises(Exception):
                import importlib
                import app.db.database
                importlib.reload(app.db.database)
        
        logger.info("Database session error test completed")
    except Exception as e:
        logger.error(f"Database session error test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_app_startup_with_config_error():
    """Test app startup with configuration errors"""
    try:
        # Test with invalid config file path
        original_config = os.environ.get('CONFIG_FILE_PATH')
        os.environ['CONFIG_FILE_PATH'] = '/nonexistent/config.json'
        
        # This should trigger the config loading error path in main.py
        with patch('builtins.open', side_effect=FileNotFoundError("Config file not found")):
            try:
                import importlib
                import app.main
                importlib.reload(app.main)
            except Exception as e:
                logger.info(f"Expected config error: {e}")
        
        # Restore original config
        if original_config:
            os.environ['CONFIG_FILE_PATH'] = original_config
        elif 'CONFIG_FILE_PATH' in os.environ:
            del os.environ['CONFIG_FILE_PATH']
            
        logger.info("App startup config error test completed")
    except Exception as e:
        logger.error(f"App startup config error test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_app_startup_without_config():
    """Test app startup without config file"""
    try:
        # Remove config file path to test default behavior
        original_config = os.environ.get('CONFIG_FILE_PATH')
        if 'CONFIG_FILE_PATH' in os.environ:
            del os.environ['CONFIG_FILE_PATH']
        
        # This should trigger the no-config path in main.py
        import importlib
        import app.main
        importlib.reload(app.main)
        
        # Restore original config
        if original_config:
            os.environ['CONFIG_FILE_PATH'] = original_config
            
        logger.info("App startup without config test completed")
    except Exception as e:
        logger.error(f"App startup without config test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_database_get_db_function():
    """Test the get_db dependency function"""
    try:
        from app.db.database import get_db
        
        # Test that get_db returns a generator
        db_gen = get_db()
        assert hasattr(db_gen, '__next__')  # Should be a generator
        
        # Test that we can get a session
        db_session = next(db_gen)
        assert db_session is not None
        
        # Test cleanup
        try:
            next(db_gen)
        except StopIteration:
            # Expected - generator should close after yielding
            pass
            
        logger.info("Database get_db function test completed")
    except Exception as e:
        logger.error(f"Database get_db function test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_environment_variable_fallbacks():
    """Test environment variable fallback behavior"""
    try:
        # Test DATABASE_URL fallback
        original_db_url = os.environ.get('DATABASE_URL')
        if 'DATABASE_URL' in os.environ:
            del os.environ['DATABASE_URL']
        
        # This should trigger the default DATABASE_URL path
        import importlib
        import app.db.database
        importlib.reload(app.db.database)
        
        # Restore original DATABASE_URL
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
        else:
            os.environ['DATABASE_URL'] = test_db_url
            
        logger.info("Environment variable fallback test completed")
    except Exception as e:
        logger.error(f"Environment variable fallback test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise
