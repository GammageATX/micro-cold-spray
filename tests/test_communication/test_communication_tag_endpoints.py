"""Tests for tag endpoints."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

import sys

from micro_cold_spray.api.communication.endpoints.tags import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.communication.models.tags import (
    TagSubscription, TagUpdate, TagMappingUpdateRequest
)
from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError
from micro_cold_spray.api.base.errors import ErrorCode, format_error
from micro_cold_spray.api.base import get_service

sys.modules['asyncssh'] = MagicMock()


@pytest.fixture
def mock_tag_cache():
    """Create mock tag cache service."""
    service = AsyncMock()
    service.get_values = AsyncMock()
    service.write_value = AsyncMock()
    service.subscribe = AsyncMock()
    service.unsubscribe = AsyncMock()
    return service


@pytest.fixture
def mock_tag_mapping():
    """Create mock tag mapping service."""
    service = AsyncMock()
    service.get_mappings = AsyncMock()
    service.update_mapping = AsyncMock()
    service.update_mapping.return_value = None  # Ensure it returns None on success
    return service


@pytest.fixture
def mock_communication_service(mock_tag_cache, mock_tag_mapping):
    """Create mock communication service with tag services."""
    service = AsyncMock(spec=CommunicationService)
    service.tag_cache = mock_tag_cache
    service.tag_mapping = mock_tag_mapping
    service.is_initialized = True
    service.is_running = True
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with tag router."""
    app = FastAPI()
    
    # Override the get_service dependency
    async def get_mock_service():
        return mock_communication_service
    
    app.dependency_overrides[get_service(CommunicationService)] = get_mock_service
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app, mock_communication_service):
    """Create test client."""
    from micro_cold_spray.api.base import _services
    _services[CommunicationService] = mock_communication_service
    client = TestClient(test_app)
    yield client
    _services.clear()


@pytest.fixture(autouse=True)
def cleanup_services():
    """Clean up services after each test."""
    yield
    from micro_cold_spray.api.base import _services
    _services.clear()


class TestTagEndpoints:
    """Test tag endpoint functionality."""

    def test_get_tag_values_success(self, client, mock_tag_cache):
        """Test successful tag values retrieval."""
        mock_tag_cache.get_values.return_value = {
            "tag1": 42.5,
            "tag2": 100.0
        }

        response = client.get("/tags/values", params={"tags": "tag1,tag2"})
        assert response.status_code == 200
        data = response.json()
        assert data["values"]["tag1"] == 42.5
        assert data["values"]["tag2"] == 100.0

        mock_tag_cache.get_values.assert_called_once_with(["tag1", "tag2"])

    def test_get_tag_values_service_error(self, client, mock_tag_cache):
        """Test tag values retrieval with service error."""
        error_context = {"tags": ["tag1", "tag2"]}
        mock_tag_cache.get_values.side_effect = ServiceError(
            "Failed to get tag values",
            error_context
        )

        response = client.get("/tags/values", params={"tags": "tag1,tag2"})
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to get tag values",
            error_context
        )
        assert data["detail"] == expected_error

    def test_get_tag_values_validation_error(self, client, mock_tag_cache):
        """Test tag values retrieval with validation error."""
        error_context = {"invalid_tags": ["tag1"]}
        mock_tag_cache.get_values.side_effect = ValidationError(
            "Invalid tag names",
            error_context
        )

        response = client.get("/tags/values", params={"tags": "tag1,tag2"})
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid tag names",
            error_context
        )
        assert data["detail"] == expected_error

    def test_write_tag_value_success(self, client, mock_tag_cache):
        """Test successful tag value writing."""
        request_data = TagUpdate(
            tag="test_tag",
            value=42.5
        ).model_dump()

        response = client.post("/tags/write", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        mock_tag_cache.write_value.assert_called_once_with("test_tag", 42.5)

    def test_write_tag_value_validation_error(self, client, mock_tag_cache):
        """Test tag value writing with validation error."""
        error_context = {"tag": "invalid_tag"}
        mock_tag_cache.write_value.side_effect = ValidationError(
            "Invalid tag name",
            error_context
        )

        request_data = TagUpdate(
            tag="invalid_tag",
            value=42.5
        ).model_dump()

        response = client.post("/tags/write", json=request_data)
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid tag name",
            error_context
        )
        assert data["detail"] == expected_error

    def test_write_tag_value_service_error(self, client, mock_tag_cache):
        """Test tag value writing with service error."""
        error_context = {"tag": "test_tag", "value": 42.5}
        mock_tag_cache.write_value.side_effect = ServiceError(
            "Failed to write tag value",
            error_context
        )

        request_data = TagUpdate(
            tag="test_tag",
            value=42.5
        ).model_dump()

        response = client.post("/tags/write", json=request_data)
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to write tag value",
            error_context
        )
        assert data["detail"] == expected_error

    def test_subscribe_to_tags_success(self, client, mock_tag_cache):
        """Test successful tag subscription."""
        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/subscribe", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        mock_tag_cache.subscribe.assert_called_once_with(
            ["tag1", "tag2"],
            "http://localhost:8000/callback"
        )

    def test_subscribe_to_tags_validation_error(self, client, mock_tag_cache):
        """Test tag subscription with validation error."""
        error_context = {"invalid_tags": ["tag1"]}
        mock_tag_cache.subscribe.side_effect = ValidationError(
            "Invalid tag names",
            error_context
        )

        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/subscribe", json=request_data)
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid tag names",
            error_context
        )
        assert data["detail"] == expected_error

    def test_subscribe_to_tags_service_error(self, client, mock_tag_cache):
        """Test tag subscription with service error."""
        error_context = {"tags": ["tag1", "tag2"]}
        mock_tag_cache.subscribe.side_effect = ServiceError(
            "Failed to subscribe to tags",
            error_context
        )

        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/subscribe", json=request_data)
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to subscribe to tags",
            error_context
        )
        assert data["detail"] == expected_error

    def test_unsubscribe_from_tags_success(self, client, mock_tag_cache):
        """Test successful tag unsubscription."""
        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/unsubscribe", json=request_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

        mock_tag_cache.unsubscribe.assert_called_once_with(
            ["tag1", "tag2"],
            "http://localhost:8000/callback"
        )

    def test_unsubscribe_from_tags_validation_error(self, client, mock_tag_cache):
        """Test tag unsubscription with validation error."""
        error_context = {"invalid_tags": ["tag1"]}
        mock_tag_cache.unsubscribe.side_effect = ValidationError(
            "Invalid tag names",
            error_context
        )

        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/unsubscribe", json=request_data)
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid tag names",
            error_context
        )
        assert data["detail"] == expected_error

    def test_unsubscribe_from_tags_service_error(self, client, mock_tag_cache):
        """Test tag unsubscription with service error."""
        error_context = {"tags": ["tag1", "tag2"]}
        mock_tag_cache.unsubscribe.side_effect = ServiceError(
            "Failed to unsubscribe from tags",
            error_context
        )

        request_data = TagSubscription(
            tags=["tag1", "tag2"],
            callback_url="http://localhost:8000/callback"
        ).model_dump()

        response = client.post("/tags/unsubscribe", json=request_data)
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to unsubscribe from tags",
            error_context
        )
        assert data["detail"] == expected_error

    def test_get_tag_mappings_success(self, client, mock_tag_mapping):
        """Test successful tag mappings retrieval."""
        mock_tag_mapping.get_mappings.return_value = {
            "tag1": "plc_tag1",
            "tag2": "plc_tag2"
        }

        response = client.get("/tags/mappings")
        assert response.status_code == 200
        data = response.json()
        assert data["mappings"]["tag1"] == "plc_tag1"
        assert data["mappings"]["tag2"] == "plc_tag2"

        mock_tag_mapping.get_mappings.assert_called_once()

    def test_get_tag_mappings_service_error(self, client, mock_tag_mapping):
        """Test tag mappings retrieval with service error."""
        error_context = {"error": "Database connection failed"}
        mock_tag_mapping.get_mappings.side_effect = ServiceError(
            "Failed to get tag mappings",
            error_context
        )

        response = client.get("/tags/mappings")
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to get tag mappings",
            error_context
        )
        assert data["detail"] == expected_error

    def test_update_tag_mapping_success(self, client, mock_tag_mapping):
        """Test successful tag mapping update."""
        request_data = TagMappingUpdateRequest(
            tag_path="tag1",
            plc_tag="plc_tag1"
        ).model_dump()

        response = client.post("/tags/mappings", json=request_data)
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
        mock_tag_mapping.update_mapping.assert_called_once_with("tag1", "plc_tag1")

    def test_update_tag_mapping_validation_error(self, client, mock_tag_mapping):
        """Test tag mapping update with validation error."""
        error_context = {"tag_path": "invalid.tag"}

        async def mock_update_mapping(*args, **kwargs):
            raise ValidationError("Invalid tag path", error_context)
        mock_tag_mapping.update_mapping.side_effect = mock_update_mapping

        request_data = TagMappingUpdateRequest(
            tag_path="invalid.tag",
            plc_tag="plc_tag1"
        ).model_dump()

        response = client.post("/tags/mappings", json=request_data)
        assert response.status_code == ErrorCode.VALIDATION_ERROR.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.VALIDATION_ERROR,
            "Invalid tag path",
            error_context
        )
        assert data["detail"] == expected_error

    def test_update_tag_mapping_service_error(self, client, mock_tag_mapping):
        """Test tag mapping update with service error."""
        error_context = {
            "tag_path": "tag1",
            "plc_tag": "plc_tag1",
            "error": "Configuration update failed"
        }

        async def mock_update_mapping(*args, **kwargs):
            raise ServiceError("Failed to update tag mapping", error_context)
        mock_tag_mapping.update_mapping.side_effect = mock_update_mapping

        request_data = TagMappingUpdateRequest(
            tag_path="tag1",
            plc_tag="plc_tag1"
        ).model_dump()

        response = client.post("/tags/mappings", json=request_data)
        assert response.status_code == ErrorCode.SERVICE_UNAVAILABLE.get_status_code()
        data = response.json()
        expected_error = format_error(
            ErrorCode.SERVICE_UNAVAILABLE,
            "Failed to update tag mapping",
            error_context
        )
        assert data["detail"] == expected_error
