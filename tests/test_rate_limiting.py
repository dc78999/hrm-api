import pytest
import time
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Set test environment
test_db_url = "postgresql://hrm_user:hrm_password@localhost:5432/hrm_db"
os.environ["DATABASE_URL"] = test_db_url

from app.middleware.rate_limiter import InMemoryRateLimiter, RateLimitMiddleware, RateLimitRule

class TestInMemoryRateLimiter:
    """Test the in-memory rate limiter core functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.persistence_file = os.path.join(self.temp_dir, "test_rates.json")
        
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_rate_limiter_allows_within_limit(self):
        """Rate limiter should allow requests within limit"""
        limiter = InMemoryRateLimiter()
        
        # First request should be allowed
        result = limiter.check_rate_limit("test_key", 3, 60)
        assert result["allowed"] is True
        assert result["remaining"] == 2
        assert result["current_count"] == 1
        
        # Second request should be allowed
        result = limiter.check_rate_limit("test_key", 3, 60)
        assert result["allowed"] is True
        assert result["remaining"] == 1
        assert result["current_count"] == 2
        
        # Third request should be allowed
        result = limiter.check_rate_limit("test_key", 3, 60)
        assert result["allowed"] is True
        assert result["remaining"] == 0
        assert result["current_count"] == 3
    
    def test_rate_limiter_blocks_over_limit(self):
        """Rate limiter should block requests over limit"""
        limiter = InMemoryRateLimiter()
        
        # Use up the limit
        for i in range(3):
            result = limiter.check_rate_limit("test_key", 3, 60)
            assert result["allowed"] is True
        
        # Next request should be blocked
        result = limiter.check_rate_limit("test_key", 3, 60)
        assert result["allowed"] is False
        assert result["remaining"] == 0
        assert result["retry_after"] == 60
        assert result["current_count"] == 3
    
    def test_rate_limiter_sliding_window(self):
        """Rate limiter should implement sliding window correctly"""
        limiter = InMemoryRateLimiter()
        
        # Mock time to test window behavior
        with patch('time.time') as mock_time:
            # Start at time 100
            mock_time.return_value = 100
            
            # Use up the limit
            for i in range(3):
                result = limiter.check_rate_limit("test_key", 3, 60)
                assert result["allowed"] is True
            
            # Should be blocked
            result = limiter.check_rate_limit("test_key", 3, 60)
            assert result["allowed"] is False
            
            # Move time forward past window
            mock_time.return_value = 161
            
            # Should be allowed again
            result = limiter.check_rate_limit("test_key", 3, 60)
            assert result["allowed"] is True
    
    def test_rate_limiter_persistence(self):
        """Rate limiter should persist and load data"""
        # Create limiter and add some data
        limiter1 = InMemoryRateLimiter(self.persistence_file)
        
        result = limiter1.check_rate_limit("persistent_key", 5, 60)
        assert result["allowed"] is True
        assert result["remaining"] == 4
        
        # Save to file
        limiter1._save_to_file()
        
        # Create new limiter instance
        limiter2 = InMemoryRateLimiter(self.persistence_file)
        
        # Should load previous state
        result = limiter2.check_rate_limit("persistent_key", 5, 60)
        assert result["allowed"] is True
        assert result["remaining"] == 3  # Should continue from where we left off

class TestRateLimitMiddleware:
    """Test the FastAPI middleware integration"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_middleware_initialization(self):
        """Middleware should initialize correctly"""
        middleware = RateLimitMiddleware(persistence_dir=self.temp_dir)
        
        assert middleware.limiter is not None
        assert len(middleware.rules) > 0
        assert "api_general" in middleware.rules
        assert "search_detailed" in middleware.rules
    
    def test_client_key_generation(self):
        """Client keys should be generated consistently"""
        middleware = RateLimitMiddleware()
        
        mock_request = MagicMock()
        mock_request.headers = {
            "X-Organization-ID": "test-org-123",
            "User-Agent": "TestClient/1.0"
        }
        mock_request.client.host = "127.0.0.1"
        
        key1 = middleware._get_client_key(mock_request, "test_rule")
        key2 = middleware._get_client_key(mock_request, "test_rule")
        
        # Same parameters should generate same key
        assert key1 == key2
        
        # Different rule should generate different key
        key3 = middleware._get_client_key(mock_request, "different_rule")
        assert key1 != key3
    
    def test_applicable_rules_selection(self):
        """Correct rules should be applied based on request path"""
        middleware = RateLimitMiddleware()
        
        # Test health endpoint
        mock_request = MagicMock()
        mock_request.url.path = "/health"
        
        rules = middleware._get_applicable_rules(mock_request)
        assert "health" in rules
        assert len(rules) == 1
        
        # Test API search endpoint
        mock_request.url.path = "/api/v1/employees/search"
        rules = middleware._get_applicable_rules(mock_request)
        assert "api_general" in rules
        assert "api_burst" in rules
        assert "search_detailed" in rules
        assert "search_burst" in rules

class TestRateLimitIntegration:
    """Integration tests with actual FastAPI application"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.temp_dir = tempfile.mkdtemp()
        os.environ["RATE_LIMIT_STORAGE"] = self.temp_dir
        
        # Import app after setting environment
        from app.main import app
        self.client = TestClient(app)
        
        # Clear rate limits before each test
        if hasattr(app.state, 'rate_limiter'):
            app.state.rate_limiter.clear_limits()
    
    def teardown_method(self):
        """Cleanup after each test method"""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_health_endpoint_rate_limiting(self):
        """Health endpoint should have its own rate limiting"""
        # Make several requests to health endpoint
        for i in range(10):
            response = self.client.get("/health")
            assert response.status_code == 200
            
            # Should have rate limiting headers
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Rule" in response.headers
            assert response.headers["X-RateLimit-Rule"] == "health"
    
    def test_api_endpoint_rate_limiting(self):
        """API endpoints should have rate limiting applied"""
        headers = {"X-Organization-ID": "124690d3-458f-4ead-8c57-532a7cd6892b"}
        
        # Make a few requests
        for i in range(3):
            response = self.client.get("/api/v1/employees/search", headers=headers)
            
            # Should succeed or fail validation, but have rate limit headers
            assert response.status_code in [200, 422]
            
            if response.status_code in [200, 422]:
                assert "X-RateLimit-Limit" in response.headers
                assert "X-RateLimit-Remaining" in response.headers
    
    def test_rate_limit_stats_endpoint(self):
        """Rate limit stats endpoint should work"""
        response = self.client.get("/health/rate-limit-stats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "limiter" in data
        assert "rules" in data
        assert "total_keys" in data["limiter"]
        assert "total_entries" in data["limiter"]
