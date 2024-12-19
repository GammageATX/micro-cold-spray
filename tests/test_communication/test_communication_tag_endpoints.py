"""Tests for tag endpoints."""

import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock

from micro_cold_spray.api.communication.endpoints.tags import router
from micro_cold_spray.api.communication.service import CommunicationService
from micro_cold_spray.api.base.exceptions import ServiceError, ValidationError


@pytest.fixture
def mock_tag_service():
    """Create mock tag service."""
    service = AsyncMock()
    return service


@pytest.fixture
def mock_communication_service(mock_tag_service):
    """Create mock communication service with tag service."""
    service = AsyncMock(spec=CommunicationService)
    service.tag_service = mock_tag_service
    return service


@pytest.fixture
def test_app(mock_communication_service):
    """Create test FastAPI app with tag router."""
    app = FastAPI()
    app.state.service = mock_communication_service
    app.include_router(router)
    return app


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestTagEndpoints:
    """Test tag endpoint functionality."""

    def test_get_tag_value_success(self, client, mock_tag_service):
        """Test successful tag value retrieval."""
        mock_tag_service.read_tag.return_value = 42.5

        response = client.get("/tags/value/test_tag")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert data["tag_id"] == "test_tag"
        assert data["value"] == 42.5

        mock_tag_service.read_tag.assert_called_once_with("test_tag")

    def test_get_tag_value_not_found(self, client, mock_tag_service):
        """Test tag value retrieval with validation error."""
        mock_tag_service.read_tag.side_effect = ValidationError(
            "Tag not found: invalid_tag"
        )

        response = client.get("/tags/value/invalid_tag")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Tag not found: invalid_tag" in data["detail"]

    def test_get_tag_value_service_error(self, client, mock_tag_service):
        """Test tag value retrieval with service error."""
        mock_tag_service.read_tag.side_effect = ServiceError(
            "Failed to read tag"
        )

        response = client.get("/tags/value/test_tag")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to read tag" in data["detail"]

    def test_list_tags_success(self, client, mock_tag_service):
        """Test successful tags list retrieval."""
        mock_tag_service.list_tags.return_value = [
            {
                "id": "tag1",
                "type": "float",
                "description": "Test tag 1"
            },
            {
                "id": "tag2",
                "type": "bool",
                "description": "Test tag 2"
            }
        ]

        response = client.get("/tags/list")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["status"] == "ok"
        assert len(data["tags"]) == 2
        assert data["tags"][0]["id"] == "tag1"
        assert data["tags"][1]["id"] == "tag2"

    def test_list_tags_service_error(self, client, mock_tag_service):
        """Test tags list with service error."""
        mock_tag_service.list_tags.side_effect = ServiceError(
            "Failed to list tags"
        )

        response = client.get("/tags/list")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to list tags" in data["detail"]

    def test_write_tag_value_success(self, client, mock_tag_service):
        """Test successful tag value write."""
        request_data = {
            "tag_id": "test_tag",
            "value": 42.5
        }

        response = client.post("/tags/write", json=request_data)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Tag test_tag written with value 42.5"

        mock_tag_service.write_tag.assert_called_once_with(
            tag_id="test_tag",
            value=42.5
        )

    def test_write_tag_value_validation_error(self, client, mock_tag_service):
        """Test tag value write with validation error."""
        mock_tag_service.write_tag.side_effect = ValidationError(
            "Invalid value type for tag"
        )

        response = client.post("/tags/write", json={
            "tag_id": "test_tag",
            "value": "invalid"
        })
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        data = response.json()
        assert "Invalid value type for tag" in data["detail"]

    def test_write_tag_value_service_error(self, client, mock_tag_service):
        """Test tag value write with service error."""
        mock_tag_service.write_tag.side_effect = ServiceError(
            "Failed to write tag"
        )

        response = client.post("/tags/write", json={
            "tag_id": "test_tag",
            "value": 42.5
        })
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to write tag" in data["detail"]

    def test_subscribe_to_tag_success(self, client, mock_tag_service):
        """Test successful tag subscription."""
        response = client.post("/tags/subscribe/test_tag")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "ok"
        assert data["message"] == "Subscribed to tag test_tag"

        mock_tag_service.subscribe_to_tag.assert_called_once_with("test_tag")

    def test_subscribe_to_tag_not_found(self, client, mock_tag_service):
        """Test tag subscription with validation error."""
        mock_tag_service.subscribe_to_tag.side_effect = ValidationError(
            "Tag not found: invalid_tag"
        )

        response = client.post("/tags/subscribe/invalid_tag")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        data = response.json()
        assert "Tag not found: invalid_tag" in data["detail"]

    def test_subscribe_to_tag_service_error(self, client, mock_tag_service):
        """Test tag subscription with service error."""
        mock_tag_service.subscribe_to_tag.side_effect = ServiceError(
            "Failed to subscribe to tag"
        )

        response = client.post("/tags/subscribe/test_tag")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert "Failed to subscribe to tag" in data["detail"]
