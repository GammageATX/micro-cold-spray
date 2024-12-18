"""Tests for UI router."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def templates_dir(tmp_path):
    """Create test templates directory."""
    templates = tmp_path / "templates"
    templates.mkdir()
    
    # Create base template
    base_html = """
    <!DOCTYPE html>
    <html>
    <head><title>Test</title></head>
    <body>{% block content %}{% endblock %}</body>
    </html>
    """
    (templates / "base.html").write_text(base_html)
    
    # Create index template
    index_html = """
    {% extends "base.html" %}
    {% block content %}
    <h1>Test</h1>
    {% endblock %}
    """
    (templates / "index.html").write_text(index_html)
    
    # Create testing directory and template
    testing = templates / "testing"
    testing.mkdir()
    testing_html = """
    {% extends "base.html" %}
    {% block content %}
    <h1>Test Scenarios</h1>
    {% endblock %}
    """
    (testing / "index.html").write_text(testing_html)
    
    return templates


@pytest.fixture
def client(templates_dir, monkeypatch):
    """Create test client with templates."""
    from micro_cold_spray.ui.router import app
    # Create new Jinja2Templates instance with test directory
    from fastapi.templating import Jinja2Templates
    test_templates = Jinja2Templates(directory=str(templates_dir))
    # Replace the templates in router
    monkeypatch.setattr('micro_cold_spray.ui.router.templates', test_templates)
    return TestClient(app)


def test_home_page(client):
    """Test home page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Test" in response.text


def test_testing_interface(client):
    """Test testing interface."""
    response = client.get("/testing")
    assert response.status_code == 200
    assert "Test Scenarios" in response.text


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "uptime" in data


def test_api_urls():
    """Test API URLs configuration."""
    from micro_cold_spray.ui.router import get_api_urls
    urls = get_api_urls()
    assert "config" in urls
    assert "communication" in urls
    assert "messaging" in urls
    assert "ws" in urls


def test_test_scenarios():
    """Test test scenarios configuration."""
    from micro_cold_spray.ui.router import get_test_scenarios
    scenarios = get_test_scenarios()
    assert "motion" in scenarios
    assert "gas" in scenarios
    assert all(
        key in scenarios["motion"]
        for key in ["name", "description", "steps"]
    )
