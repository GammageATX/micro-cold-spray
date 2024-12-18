"""API test utilities."""

from typing import Dict, Any, Optional
from fastapi.testclient import TestClient


def assert_api_error(
    client: TestClient,
    endpoint: str,
    expected_code: int,
    expected_message: Optional[str] = None,
    method: str = "GET",
    json: Optional[Dict[str, Any]] = None
):
    """Assert API error response matches expected format.
    
    Args:
        client: TestClient instance
        endpoint: API endpoint to test
        expected_code: Expected HTTP status code
        expected_message: Expected error message (optional)
        method: HTTP method to use
        json: Request JSON data (optional)
    """
    if method == "GET":
        response = client.get(endpoint)
    elif method == "POST":
        response = client.post(endpoint, json=json)
    elif method == "PUT":
        response = client.put(endpoint, json=json)
    elif method == "DELETE":
        response = client.delete(endpoint)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
        
    assert response.status_code == expected_code
    if expected_message:
        assert expected_message in response.text


def assert_api_success(
    client: TestClient,
    endpoint: str,
    expected_data: Optional[Dict[str, Any]] = None,
    method: str = "GET",
    json: Optional[Dict[str, Any]] = None
):
    """Assert API success response matches expected format.
    
    Args:
        client: TestClient instance
        endpoint: API endpoint to test
        expected_data: Expected response data (optional)
        method: HTTP method to use
        json: Request JSON data (optional)
    """
    if method == "GET":
        response = client.get(endpoint)
    elif method == "POST":
        response = client.post(endpoint, json=json)
    elif method == "PUT":
        response = client.put(endpoint, json=json)
    elif method == "DELETE":
        response = client.delete(endpoint)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
        
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    
    if expected_data:
        assert "data" in data
        assert data["data"] == expected_data
