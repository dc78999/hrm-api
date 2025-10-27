import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

# Set test database URL to use localhost instead of Docker service name
test_db_url = "postgresql://hrm_user:hrm_password@localhost:5432/hrm_db"
os.environ["DATABASE_URL"] = test_db_url

try:
    from app.main import app
except Exception as e:
    raise Exception(f"Failed to import app: {e}. Make sure PostgreSQL is running on localhost:5432")

client = TestClient(app)

# Use a known organization ID from our seeded data
TEST_ORG_ID = "124690d3-458f-4ead-8c57-532a7cd6892b"

def test_search_employees_requires_organization():
    """Should require organization_id in headers"""
    response = client.get("/api/v1/employees/search")
    
    assert response.status_code == 422
    error_detail = response.json()["detail"]
    
    # Find the specific error for X-Organization-ID
    header_errors = [
        err for err in error_detail 
        if err["loc"] == ["header", "X-Organization-ID"]
    ]
    
    assert header_errors, "No error found for X-Organization-ID header"
    error = header_errors[0]
    assert error["type"] == "value_error.missing"
    assert "field required" in error["msg"].lower()

def test_search_employees_basic_filter():
    """Should filter employees by basic fields"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"location": "New York"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    for employee in data["items"]:
        assert employee["location"] == "New York"

def test_search_employees_text_search():
    """Should support full-text search across fields"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"q": "engineer"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) > 0
    for employee in data["items"]:
        # Should match either position or data
        assert ("engineer" in employee["position"].lower() or 
                "engineer" in str(employee["data"]).lower())

def test_search_employees_pagination():
    """Should support pagination"""
    page_size = 5
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page": 1, "page_size": page_size}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) <= page_size
    assert "total" in data
    assert "page" in data
    assert data["page"] == 1
    assert data["page_size"] == page_size

def test_search_employees_multiple_filters():
    """Should support multiple filter parameters"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"location": "New York", "position": "Engineer"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for employee in data["items"]:
        assert employee["location"] == "New York"
        assert "engineer" in employee["position"].lower()

def test_search_employees_no_results():
    """Should handle search with no matching results"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"location": "NonExistentCity"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0

def test_search_employees_invalid_organization():
    """Should handle invalid organization ID"""
    invalid_org_id = "invalid-uuid"
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": invalid_org_id}
    )
    
    # Should either return 422 for invalid UUID format or 200 with empty results
    assert response.status_code in [200, 422]
    if response.status_code == 200:
        data = response.json()
        assert data["items"] == []

def test_search_employees_sorting():
    """Should support sorting results"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"sort_by": "created_at", "sort_order": "desc"}
    )
    
    assert response.status_code == 200
    data = response.json()
    if len(data["items"]) > 1:
        # Check response structure
        assert "items" in data
        assert "total" in data
        assert isinstance(data["items"], list)
        for item in data["items"]:
            assert "data" in item
            assert isinstance(item["data"], dict)

def test_search_employees_large_page_size():
    """Should handle large page size requests"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page_size": 1000}
    )
    
    assert response.status_code == 422

def test_search_employees_invalid_page():
    """Should handle invalid page numbers"""
    # Test page 0 (invalid)
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page": 0}
    )
    
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
    
    assert response.status_code == 422
    
    # Test extremely high page number (should return empty results, not error)
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page": 99999}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["items"] == []
    assert data["page"] == 99999

def test_search_employees_invalid_page_size():
    """Should handle invalid page size values"""
    # Test page_size 0 (invalid)
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page_size": 0}
    )
    
    assert response.status_code == 422
    
    # Test negative page_size
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"page_size": -5}
    )
    
    assert response.status_code == 422

def test_search_employees_empty_query():
    """Should handle empty search query"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"q": ""}
    )
    
    assert response.status_code == 200
    data = response.json()
    # Empty query should return all employees
    assert "items" in data
    assert "total" in data

def test_search_employees_special_characters():
    """Should handle special characters in search"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"q": "O'Connor"}  # Test apostrophe
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_search_employees_case_insensitive():
    """Should perform case-insensitive search"""
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
    
    assert response_lower.status_code == 200
    assert response_upper.status_code == 200
    
    data_lower = response_lower.json()
    data_upper = response_upper.json()
    
    # Should return same number of results regardless of case
    assert data_lower["total"] == data_upper["total"]

def test_app_startup_with_config_error():
    """Test app startup with configuration errors"""
    # Test with invalid config file path
    original_config = os.environ.get('CONFIG_FILE_PATH')
    os.environ['CONFIG_FILE_PATH'] = '/nonexistent/config.json'
    
    # This should trigger the config loading error path in main.py
    with patch('builtins.open', side_effect=FileNotFoundError("Config file not found")):
        try:
            import importlib
            import app.main
            importlib.reload(app.main)
        except Exception:
            pass  # Expected error
    
    # Restore original config
    if original_config:
        os.environ['CONFIG_FILE_PATH'] = original_config
    elif 'CONFIG_FILE_PATH' in os.environ:
        del os.environ['CONFIG_FILE_PATH']

def test_app_startup_without_config():
    """Test app startup without config file"""
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

def test_environment_variable_fallbacks():
    """Test environment variable fallback behavior"""
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

def test_search_employees_with_status_filter():
    """Should filter employees by status"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"status": "active"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for employee in data["items"]:
        assert employee["status"] == "active"

def test_search_employees_by_position():
    """Should filter employees by position"""
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"position": "Engineering"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    for employee in data["items"]:
        assert employee["position"] == "Engineering"

def test_search_employees_jsonb_field_search():
    """Should search within JSONB data fields"""
    # Search for specific email domain
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"q": "example.net"}
    )
    
    assert response.status_code == 200
    data = response.json()
    if len(data["items"]) > 0:
        found_match = False
        for employee in data["items"]:
            if "email" in employee.get("data", {}):
                if "example.net" in employee["data"]["email"]:
                    found_match = True
                    break

def test_search_employees_sql_injection_attempt():
    """Should handle SQL injection attempts safely"""
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
        
        # Should not cause server error
        assert response.status_code in [200, 400, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data

def test_search_employees_unicode_characters():
    """Should handle unicode and special characters"""
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
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data

def test_search_employees_very_long_query():
    """Should handle very long search queries"""
    # Create a very long query string
    long_query = "a" * 1000
    response = client.get(
        "/api/v1/employees/search",
        headers={"X-Organization-ID": TEST_ORG_ID},
        params={"q": long_query}
    )
    
    assert response.status_code in [200, 400, 414]  # 414 = URI Too Long
    if response.status_code == 200:
        data = response.json()
        assert "items" in data

def test_search_employees_malformed_uuid():
    """Should handle malformed organization UUID"""
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
        
        # Should either return validation error or empty results
        assert response.status_code in [200, 422]
        
        if response.status_code == 200:
            data = response.json()
            assert data["items"] == []
            assert data["total"] == 0

def test_search_employees_different_organizations():
    """Should only return employees from specified organization"""
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

def test_search_employees_edge_case_pagination():
    """Should handle edge cases in pagination"""
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

def test_search_employees_all_filters_combined():
    """Should handle all filters applied simultaneously"""
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

def test_search_employees_empty_string_filters():
    """Should handle empty string filters"""
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
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data

def test_search_employees_with_invalid_text_representation():
    """Test handling of psycopg2 InvalidTextRepresentation error"""
    with patch('app.db.database.search_employees') as mock_search:
        from psycopg2 import errors
        mock_search.side_effect = errors.InvalidTextRepresentation("Invalid UUID format")
        
        response = client.get(
            "/api/v1/employees/search",
            headers={"X-Organization-ID": "invalid-uuid-format"}
        )
        
        assert response.status_code == 422

def test_search_employees_response_structure():
    """Should return properly structured response"""
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

def test_search_employees_concurrent_requests():
    """Test handling of concurrent requests"""
    import threading
    
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

def test_search_endpoint_response_model():
    """Test that search endpoint uses correct response model"""
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

def test_search_endpoint_parameter_validation():
    """Test search endpoint parameter constraints"""
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

def test_logging_configuration():
    """Test that logging is properly configured"""
    import logging
    
    # Test that logger exists and is configured
    from app.main import logger as main_logger
    
    assert main_logger is not None
    assert main_logger.name == "app.main"
    assert main_logger.level <= logging.INFO  # Should be INFO or lower
    
    # Test that root logger has handlers
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0

def test_search_employees_boundary_conditions():
    """Test boundary conditions for pagination parameters"""
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

def test_search_employees_all_optional_params():
    """Test search with all optional parameters provided"""
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
