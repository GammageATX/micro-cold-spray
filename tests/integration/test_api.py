"""Integration tests for main API functionality."""

import pytest
from fastapi import status

class TestMainAPI:
    """Test cases for main API functionality."""
    
    def test_service_mounting(self, main_client):
        """Test service applications are mounted correctly."""
        # Test config service
        response = main_client.get("/api/config/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test communication service
        response = main_client.get("/api/communication/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test process service
        response = main_client.get("/api/process/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test state service
        response = main_client.get("/api/state/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test data collection service
        response = main_client.get("/api/data/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test validation service
        response = main_client.get("/api/validation/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test messaging service
        response = main_client.get("/api/messaging/health")
        assert response.status_code == status.HTTP_200_OK
        
        # Test UI
        response = main_client.get("/ui/health")
        assert response.status_code == status.HTTP_200_OK
    
    def test_cors_middleware(self, main_client):
        """Test CORS middleware configuration."""
        response = main_client.options(
            "/api/config/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type"
            }
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.headers["access-control-allow-origin"] == "*"
        assert response.headers["access-control-allow-methods"] == "*"
        assert response.headers["access-control-allow-headers"] == "*"
    
    def test_service_isolation(self, main_client):
        """Test services are properly isolated."""
        # Test invalid service path
        response = main_client.get("/api/invalid/health")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test invalid endpoint on valid service
        response = main_client.get("/api/config/invalid")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        
        # Test cross-service access
        response = main_client.get("/api/config/state")
        assert response.status_code == status.HTTP_404_NOT_FOUND 