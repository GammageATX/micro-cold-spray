"""Test configurable service module."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from micro_cold_spray.api.base.base_app import create_app
from tests.test_base.conftest import (
    TestConfig,
    TestConfigurableService,
    InvalidConfigurableService
)


def test_configurable_service():
    """Test configurable service initialization."""
    app = create_app(
        service_class=TestConfigurableService,
        title="Test API"
    )
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        # Service should not be healthy until configured
        assert not data["is_healthy"]
        assert data["services"][0]["status"] == "unconfigured"


def test_invalid_service():
    """Test invalid configurable service."""
    with pytest.raises(TypeError) as exc:
        create_app(
            service_class=InvalidConfigurableService,
            title="Test API"
        )
    assert "config_model" in str(exc.value)


def test_configure_service():
    """Test service configuration."""
    app = create_app(
        service_class=TestConfigurableService,
        title="Test API"
    )
    config = TestConfig(
        value=42,
        name="test",
        required_field="required"
    )
    with TestClient(app) as client:
        # Configure service
        response = client.post("/config", json=config.model_dump())
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == 42
        assert data["name"] == "test"
        assert data["required_field"] == "required"

        # Check health after configuration
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["is_healthy"]
        assert data["services"][0]["status"] == "running"


def test_invalid_configuration():
    """Test invalid configuration handling."""
    app = create_app(
        service_class=TestConfigurableService,
        title="Test API"
    )
    with TestClient(app) as client:
        # Missing required field
        response = client.post("/config", json={
            "value": 42,
            "name": "test"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert "required_field" in str(data["detail"])

        # Invalid value type
        response = client.post("/config", json={
            "value": "not_a_number",
            "name": "test",
            "required_field": "required"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "detail" in data
        assert "value" in str(data["detail"])

        # Check service remains unconfigured
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert not data["is_healthy"]
        assert data["services"][0]["status"] == "unconfigured"


def test_reconfigure_service():
    """Test reconfiguring service."""
    app = create_app(
        service_class=TestConfigurableService,
        title="Test API"
    )
    config = TestConfig(
        value=42,
        name="test",
        required_field="required"
    )
    with TestClient(app) as client:
        # Initial configuration
        response = client.post("/config", json=config.model_dump())
        assert response.status_code == 200

        # Try to reconfigure
        config.value = 84
        response = client.post("/config", json=config.model_dump())
        assert response.status_code == status.HTTP_409_CONFLICT
        data = response.json()
        assert "already configured" in data["detail"]["message"]
