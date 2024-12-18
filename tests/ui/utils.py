"""UI test utilities."""

from typing import Dict, Any, Optional
from fastapi.testclient import TestClient


def assert_ui_response(
    client: TestClient,
    endpoint: str,
    expected_template: str,
    expected_context: Optional[Dict[str, Any]] = None
):
    """Assert UI response matches expected format.
    
    Args:
        client: TestClient instance
        endpoint: UI endpoint to test
        expected_template: Expected template name
        expected_context: Expected template context (optional)
    """
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.template.name == expected_template
    if expected_context:
        for key, value in expected_context.items():
            assert key in response.context
            assert response.context[key] == value


def assert_ui_error(
    client: TestClient,
    endpoint: str,
    expected_code: int,
    expected_template: str = "error.html",
    expected_message: Optional[str] = None
):
    """Assert UI error response matches expected format.
    
    Args:
        client: TestClient instance
        endpoint: UI endpoint to test
        expected_code: Expected HTTP status code
        expected_template: Expected error template name
        expected_message: Expected error message (optional)
    """
    response = client.get(endpoint)
    assert response.status_code == expected_code
    assert response.template.name == expected_template
    if expected_message:
        assert expected_message in response.text


def assert_ui_redirect(
    client: TestClient,
    endpoint: str,
    expected_location: str,
    method: str = "GET",
    data: Optional[Dict[str, Any]] = None
):
    """Assert UI redirect response matches expected format.
    
    Args:
        client: TestClient instance
        endpoint: UI endpoint to test
        expected_location: Expected redirect location
        method: HTTP method to use
        data: Form data (optional)
    """
    if method == "GET":
        response = client.get(endpoint, follow=False)
    elif method == "POST":
        response = client.post(endpoint, data=data, follow=False)
    else:
        raise ValueError(f"Unsupported HTTP method: {method}")
        
    assert response.status_code == 302
    assert response.headers["location"] == expected_location
