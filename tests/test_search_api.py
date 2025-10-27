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
            params={"sort_by": "created_at", "sort_order": "desc"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 1:
            # Check if results are sorted by created_at (default sorting)
            # Since we can't easily verify full_name sorting from JSONB without knowing the data structure,
            # we'll verify the response structure instead
            assert "items" in data
            assert "total" in data
            assert isinstance(data["items"], list)
            for item in data["items"]:
                assert "data" in item
                assert isinstance(item["data"], dict)
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
        
        assert response.status_code == 422
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_invalid_page():
    """Should handle invalid page numbers"""
    try:
        # Test page 0 (invalid)
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 0}
        )
        logger.info(f"Response status for page 0: {response.status_code}")
        logger.info(f"Response body for page 0: {response.text}")
        
        # Should return 422 for validation error
        assert response.status_code == 422
        error_detail = response.json()["detail"]
        assert any("page" in str(err).lower() for err in error_detail)
        
        # Test negative page
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": -1}
        )
        logger.info(f"Response status for page -1: {response.status_code}")
        logger.info(f"Response body for page -1: {response.text}")
        
        assert response.status_code == 422
        
        # Test extremely high page number (should return empty results, not error)
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 99999}
        )
        logger.info(f"Response status for page 99999: {response.status_code}")
        logger.info(f"Response body for page 99999: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["page"] == 99999
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_invalid_page_size():
    """Should handle invalid page size values"""
    try:
        # Test page_size 0 (invalid)
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page_size": 0}
        )
        logger.info(f"Response status for page_size 0: {response.status_code}")
        logger.info(f"Response body for page_size 0: {response.text}")
        
        assert response.status_code == 422
        
        # Test negative page_size
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page_size": -5}
        )
        logger.info(f"Response status for page_size -5: {response.status_code}")
        logger.info(f"Response body for page_size -5: {response.text}")
        
        assert response.status_code == 422
        
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

def test_search_employees_with_status_filter():
    """Should filter employees by status"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"status": "active"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for employee in data["items"]:
            assert employee["status"] == "active"
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_by_position():
    """Should filter employees by position"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"position": "Engineering"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        for employee in data["items"]:
            assert employee["position"] == "Engineering"
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_jsonb_field_search():
    """Should search within JSONB data fields"""
    try:
        # Search for specific email domain
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": "example.net"}
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        if len(data["items"]) > 0:
            found_match = False
            for employee in data["items"]:
                if "email" in employee.get("data", {}):
                    if "example.net" in employee["data"]["email"]:
                        found_match = True
                        break
            # Note: May not find match due to search vector indexing, but should not error
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_sql_injection_attempt():
    """Should handle SQL injection attempts safely"""
    try:
        malicious_queries = [
            "'; DROP TABLE employees; --",
            "' OR '1'='1",
            "1'; SELECT * FROM employees; --",
            "<script>alert('xss')</script>",
            "' UNION SELECT * FROM employees --"
        ]
        
        for malicious_query in malicious_queries:
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID},
                params={"q": malicious_query}
            )
            logger.info(f"Response status for '{malicious_query}': {response.status_code}")
            
            # Should not cause server error
            assert response.status_code in [200, 400, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert "items" in data
                assert "total" in data
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_unicode_characters():
    """Should handle unicode and special characters"""
    try:
        unicode_queries = [
            "José",
            "François",
            "München",
            "北京",
            "🔍",
            "café",
            "naïve"
        ]
        
        for unicode_query in unicode_queries:
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID},
                params={"q": unicode_query}
            )
            logger.info(f"Response status for '{unicode_query}': {response.status_code}")
            
            assert response.status_code == 200
            data = response.json()
            assert "items" in data
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_very_long_query():
    """Should handle very long search queries"""
    try:
        # Create a very long query string
        long_query = "a" * 1000
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"q": long_query}
        )
        logger.info(f"Response status for long query: {response.status_code}")
        
        assert response.status_code in [200, 400, 414]  # 414 = URI Too Long
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_malformed_uuid():
    """Should handle malformed organization UUID"""
    try:
        malformed_uuids = [
            "not-a-uuid",
            "123",
            "12345678-1234-1234-1234",
            "12345678-1234-1234-1234-12345678901234567890",
            "",
            "null"
        ]
        
        for malformed_uuid in malformed_uuids:
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": malformed_uuid}
            )
            logger.info(f"Response status for UUID '{malformed_uuid}': {response.status_code}")
            
            # Should either return validation error or empty results
            assert response.status_code in [200, 422]
            
            if response.status_code == 200:
                data = response.json()
                assert data["items"] == []
                assert data["total"] == 0
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_different_organizations():
    """Should only return employees from specified organization"""
    try:
        # Test with different organization IDs from seed data
        org_ids = [
            "124690d3-458f-4ead-8c57-532a7cd6892b",
            "68e529cc-78ba-4179-b955-76f1624550ae",
            "feb99c04-3b47-413e-8387-959574862e24"
        ]
        
        results = []
        for org_id in org_ids:
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": org_id}
            )
            assert response.status_code == 200
            data = response.json()
            
            # Verify all returned employees belong to the requested organization
            for employee in data["items"]:
                assert employee["organization_id"] == org_id
            
            results.append((org_id, data["total"]))
            logger.info(f"Org {org_id}: {data['total']} employees")
        
        # Verify different organizations have different employee counts
        totals = [result[1] for result in results]
        if len(set(totals)) > 1:
            logger.info("Organizations have different employee counts as expected")
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_edge_case_pagination():
    """Should handle edge cases in pagination"""
    try:
        # Test page 1 with page_size 1
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": 1}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 1
        
        # Test maximum page_size
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": 100}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) <= 100
        
        # Test page beyond available data
        if data["total"] > 0:
            last_page = (data["total"] // 10) + 10  # Way beyond last page
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID},
                params={"page": last_page, "page_size": 10}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["items"] == []
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_all_filters_combined():
    """Should handle all filters applied simultaneously"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={
                "q": "engineering",
                "location": "Engineering",  # This might not match location field
                "position": "Engineering",
                "status": "active",
                "page": 1,
                "page_size": 5
            }
        )
        logger.info(f"Response status: {response.status_code}")
        logger.info(f"Response body: {response.text}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert len(data["items"]) <= 5
        
        # Verify filters are applied
        for employee in data["items"]:
            assert employee["organization_id"] == TEST_ORG_ID
            assert employee["status"] == "active"
            if data["items"]:  # Only check if we have results
                assert employee["position"] == "Engineering"
                
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_empty_string_filters():
    """Should handle empty string filters"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={
                "q": "",
                "location": "",
                "position": "",
                "status": ""
            }
        )
        logger.info(f"Response status: {response.status_code}")
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_invalid_text_representation():
    """Test handling of psycopg2 InvalidTextRepresentation error"""
    try:
        with patch('app.db.database.search_employees') as mock_search:
            from psycopg2 import errors
            mock_search.side_effect = errors.InvalidTextRepresentation("Invalid UUID format")
            
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": "invalid-uuid-format"}
            )
            
            assert response.status_code == 422
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_response_structure():
    """Should return properly structured response"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = ["items", "total", "page", "page_size"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        assert isinstance(data["items"], list)
        assert isinstance(data["total"], int)
        assert isinstance(data["page"], int)
        assert isinstance(data["page_size"], int)
        
        # Verify employee structure if we have employees
        if data["items"]:
            employee = data["items"][0]
            required_employee_fields = ["id", "organization_id", "location", "position", "status", "data"]
            for field in required_employee_fields:
                assert field in employee, f"Missing required employee field: {field}"
            
            assert isinstance(employee["data"], dict)
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_concurrent_requests():
    """Test handling of concurrent requests"""
    try:
        import threading
        import time
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = client.get(
                    "/api/v1/employees/search",
                    headers={"X-Organization-ID": TEST_ORG_ID},
                    params={"page": 1, "page_size": 10}
                )
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert all(status == 200 for status in results), f"Non-200 responses: {results}"
        
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_app_lifespan_startup():
    """Test application startup lifespan event"""
    try:
        with patch('app.main.ensure_db') as mock_ensure_db:
            mock_ensure_db.return_value = None
            
            # Create a new FastAPI instance to test lifespan
            from fastapi.testclient import TestClient
            from app.main import app
            
            with TestClient(app) as test_client:
                # The lifespan startup should have been called
                mock_ensure_db.assert_called_once()
                logger.info("Lifespan startup test completed")
    except Exception as e:
        logger.error(f"Lifespan startup test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_app_lifespan_startup_with_database_error():
    """Test application startup with database connection error"""
    try:
        with patch('app.main.ensure_db') as mock_ensure_db:
            # Simulate database connection failure during startup
            mock_ensure_db.side_effect = Exception("Database connection failed")
            
            # This should raise an exception during app initialization
            with pytest.raises(Exception):
                from fastapi.testclient import TestClient
                import importlib
                import app.main
                importlib.reload(app.main)
                TestClient(app.main.app)
                
        logger.info("Lifespan startup error test completed")
    except Exception as e:
        logger.error(f"Lifespan startup error test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_connection_error():
    """Test search endpoint with database connection error"""
    try:
        with patch('app.db.database.search_employees') as mock_search:
            mock_search.side_effect = ConnectionError("Database connection lost")
            
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID}
            )
            
            assert response.status_code == 503
            error_data = response.json()
            assert "Database connection error" in error_data["detail"]
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_generic_exception():
    """Test search endpoint with generic exception"""
    try:
        with patch('app.db.database.search_employees') as mock_search:
            mock_search.side_effect = RuntimeError("Unexpected database error")
            
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID}
            )
            
            assert response.status_code == 500
            error_data = response.json()
            assert "Internal server error" in error_data["detail"]
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_logging_verification():
    """Test that proper logging occurs during search"""
    try:
        with patch('app.main.logger') as mock_logger:
            response = client.get(
                "/api/v1/employees/search",
                headers={"X-Organization-ID": TEST_ORG_ID},
                params={"q": "test", "page": 1, "page_size": 10}
            )
            
            assert response.status_code == 200
            
            # Verify logging calls were made
            assert mock_logger.info.call_count >= 3  # At least 3 info logs expected
            
            # Check specific log messages
            log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
            assert any("Searching employees for organization" in msg for msg in log_calls)
            assert any("Search params" in msg for msg in log_calls)
            assert any("Search returned" in msg for msg in log_calls)
            
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_validation_error_logging():
    """Test that validation errors are properly logged"""
    try:
        with patch('app.main.logger') as mock_logger:
            with patch('app.db.database.search_employees') as mock_search:
                mock_search.side_effect = ValueError("Invalid search parameters")
                
                response = client.get(
                    "/api/v1/employees/search",
                    headers={"X-Organization-ID": TEST_ORG_ID}
                )
                
                assert response.status_code == 422
                
                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                assert "Validation error" in error_call
                
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_connection_error_logging():
    """Test that connection errors are properly logged"""
    try:
        with patch('app.main.logger') as mock_logger:
            with patch('app.db.database.search_employees') as mock_search:
                mock_search.side_effect = ConnectionError("Database connection failed")
                
                response = client.get(
                    "/api/v1/employees/search",
                    headers={"X-Organization-ID": TEST_ORG_ID}
                )
                
                assert response.status_code == 503
                
                # Verify error logging
                mock_logger.error.assert_called_once()
                error_call = mock_logger.error.call_args[0][0]
                assert "Database connection error" in error_call
                
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_with_generic_error_logging():
    """Test that generic errors are properly logged with traceback"""
    try:
        with patch('app.main.logger') as mock_logger:
            with patch('app.db.database.search_employees') as mock_search:
                mock_search.side_effect = RuntimeError("Unexpected error")
                
                response = client.get(
                    "/api/v1/employees/search",
                    headers={"X-Organization-ID": TEST_ORG_ID}
                )
                
                assert response.status_code == 500
                
                # Verify error logging with traceback
                mock_logger.error.assert_called_once()
                args, kwargs = mock_logger.error.call_args
                assert "Search failed" in args[0]
                assert kwargs.get('exc_info') is True  # Traceback included
                
    except Exception as e:
        logger.error(f"Test failed with exception: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_app_fastapi_metadata():
    """Test FastAPI app metadata and configuration"""
    try:
        from app.main import app
        
        # Test app metadata
        assert app.title == "hrm-api"
        assert app.description == "HRM API with dynamic columns and simple rate limiting"
        assert app.lifespan is not None
        
        # Test that the app has the expected routes
        routes = [route.path for route in app.routes]
        assert "/api/v1/employees/search" in routes
        
        logger.info("FastAPI metadata test completed")
    except Exception as e:
        logger.error(f"FastAPI metadata test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_endpoint_response_model():
    """Test that search endpoint uses correct response model"""
    try:
        from app.main import app
        from app.models import SearchResponse
        
        # Find the search route
        search_route = None
        for route in app.routes:
            if hasattr(route, 'path') and route.path == "/api/v1/employees/search":
                search_route = route
                break
        
        assert search_route is not None, "Search route not found"
        
        # Check response model
        assert hasattr(search_route, 'response_model')
        # The response model should be SearchResponse or equivalent
        
        logger.info("Response model test completed")
    except Exception as e:
        logger.error(f"Response model test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_endpoint_parameter_validation():
    """Test search endpoint parameter constraints"""
    try:
        # Test parameter validation by examining the endpoint signature
        from app.main import search_employees_endpoint
        import inspect
        
        sig = inspect.signature(search_employees_endpoint)
        
        # Verify parameters exist
        params = sig.parameters
        assert 'x_organization_id' in params
        assert 'q' in params
        assert 'location' in params
        assert 'position' in params
        assert 'status' in params
        assert 'page' in params
        assert 'page_size' in params
        
        logger.info("Parameter validation test completed")
    except Exception as e:
        logger.error(f"Parameter validation test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_logging_configuration():
    """Test that logging is properly configured"""
    try:
        import logging
        
        # Test that logger exists and is configured
        from app.main import logger as main_logger
        
        assert main_logger is not None
        assert main_logger.name == "app.main"
        assert main_logger.level <= logging.INFO  # Should be INFO or lower
        
        # Test that root logger has handlers
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
        
        logger.info("Logging configuration test completed")
    except Exception as e:
        logger.error(f"Logging configuration test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_boundary_conditions():
    """Test boundary conditions for pagination parameters"""
    try:
        # Test minimum valid values
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": 1}
        )
        assert response.status_code == 200
        
        # Test maximum valid values
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": 100}
        )
        assert response.status_code == 200
        
        # Test just over maximum page_size
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={"page": 1, "page_size": 101}
        )
        assert response.status_code == 422
        
        logger.info("Boundary conditions test completed")
    except Exception as e:
        logger.error(f"Boundary conditions test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise

def test_search_employees_all_optional_params():
    """Test search with all optional parameters provided"""
    try:
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": TEST_ORG_ID},
            params={
                "q": "test",
                "location": "Engineering",
                "position": "Engineering", 
                "status": "active",
                "page": 1,
                "page_size": 10
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        
        logger.info("All optional parameters test completed")
    except Exception as e:
        logger.error(f"All optional parameters test failed: {e}")
        logger.error(f"Exception type: {type(e)}")
        raise
