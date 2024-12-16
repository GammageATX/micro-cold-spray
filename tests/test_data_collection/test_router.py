"""Tests for data collection router."""

from datetime import datetime
import json
from typing import AsyncGenerator
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient
import httpx
from fastapi.encoders import jsonable_encoder

from micro_cold_spray.api.data_collection.router import get_service, router
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj: object) -> str:
        """Convert datetime to ISO format string."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


# Test data
SAMPLE_EVENT = SprayEvent(
    id=None,
    sequence_id="test_sequence_1",
    spray_index=1,
    timestamp=datetime.now(),
    x_pos=1.0,
    y_pos=2.0,
    z_pos=3.0,
    pressure=100.0,
    temperature=25.0,
    flow_rate=5.0,
    status="completed"
)

COLLECTION_PARAMS = {
    "mode": "continuous",
    "interval": 1.0,
    "duration": 60.0
}


@pytest.fixture
def mock_service() -> Mock:
    """Create a mock data collection service."""
    service = Mock(spec=DataCollectionService)
    service.start_collection = AsyncMock()
    service.stop_collection = AsyncMock()
    service.record_spray_event = AsyncMock()
    service.get_sequence_events = AsyncMock(return_value=[])
    service.check_health = AsyncMock(return_value={"status": "ok"})
    service.is_running = True
    return service


@pytest.fixture
def app(mock_service: Mock) -> FastAPI:
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_service] = lambda: mock_service
    
    # Configure JSON encoder for datetime
    app.json_encoder = DateTimeEncoder
    return app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(
        app=app,
        base_url="http://test"
    ) as client:
        yield client


def serialize_model(model):
    """Serialize a model for JSON encoding."""
    return jsonable_encoder(model)


class TestRequestValidation:
    """Test request validation and error handling."""
    
    @pytest.mark.asyncio
    async def test_sequence_id_validation(self, async_client):
        """Test sequence ID validation in various endpoints."""
        # Test empty sequence ID
        response = await async_client.post("/data-collection/start", params={"sequence_id": ""})
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
        
        # Test invalid characters in sequence ID
        response = await async_client.get("/data-collection/events/invalid#sequence@id")
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
        
        # Test sequence ID length limits
        long_id = "a" * 101
        response = await async_client.post("/data-collection/start", params={"sequence_id": long_id})
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
    
    @pytest.mark.asyncio
    async def test_collection_params_validation(self, async_client):
        """Test collection parameters validation."""
        # Test missing required params
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json={}
        )
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
        
        # Test invalid parameter types
        invalid_params = {
            "interval": "invalid",
            "max_events": -1,
            "buffer_size": 0
        }
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=invalid_params
        )
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
        
        # Test parameter range validation
        invalid_ranges = {
            "interval": 0.0,
            "max_events": 1000000,
            "buffer_size": -1
        }
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=invalid_ranges
        )
        assert response.status_code == 422  # FastAPI validation error
        assert "value_error" in response.json()["detail"][0]["type"]
    
    @pytest.mark.asyncio
    async def test_spray_event_validation(self, async_client):
        """Test spray event data validation."""
        # Test missing required fields
        incomplete_event = {
            "sequence_id": "test_sequence",
            "spray_index": 1
        }
        response = await async_client.post(
            "/data-collection/events",
            json=incomplete_event
        )
        assert response.status_code == 422
        
        # Test invalid field types
        invalid_types = SAMPLE_EVENT.model_dump()
        invalid_types["pressure"] = "invalid"
        invalid_types["spray_index"] = 1.5
        response = await async_client.post(
            "/data-collection/events",
            json=invalid_types
        )
        assert response.status_code == 422
        
        # Test field range validation
        invalid_ranges = SAMPLE_EVENT.model_dump()
        invalid_ranges["pressure"] = -1.0
        invalid_ranges["temperature"] = -300.0
        response = await async_client.post(
            "/data-collection/events",
            json=invalid_ranges
        )
        assert response.status_code == 422


class TestResponseFormatting:
    """Test response formatting and content types."""
    
    @pytest.mark.asyncio
    async def test_successful_response_format(self, async_client, mock_service):
        """Test successful response formatting."""
        # Test collection start response
        session = CollectionSession(
            sequence_id="test_sequence",
            start_time=datetime.now(),
            collection_params=COLLECTION_PARAMS
        )
        mock_service.start_collection.return_value = session
        mock_service.is_running = True  # Ensure service appears running
        
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=COLLECTION_PARAMS
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sequence_id"] == session.sequence_id
        assert "start_time" in data
        assert data["collection_params"] == COLLECTION_PARAMS
        
        # Test events response
        events = [SAMPLE_EVENT.model_copy(update={"spray_index": i}) for i in range(3)]
        mock_service.get_sequence_events.return_value = events
        response = await async_client.get("/data-collection/events/test_sequence")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3
        assert all("spray_index" in event for event in data)
    
    @pytest.mark.asyncio
    async def test_error_response_format(self, async_client, mock_service):
        """Test error response formatting."""
        # Test service error
        mock_service.start_collection.side_effect = DataCollectionError("Test error")
        mock_service.is_running = True  # Ensure service appears running
        
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=COLLECTION_PARAMS
        )
        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        assert "error" in data["detail"]
        assert data["detail"]["error"] == "Test error"
        
        # Test validation error response
        response = await async_client.post(
            "/data-collection/events",
            json={"invalid": "data"}
        )
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
    
    @pytest.mark.asyncio
    async def test_health_check_response(self, async_client, mock_service):
        """Test health check response format."""
        # Test healthy response
        mock_service.is_running = True  # Ensure service appears running
        mock_service.check_health.return_value = {
            "status": "ok",
            "active_sequence": "test_sequence",
            "uptime": 3600,
            "event_count": 100
        }
        response = await async_client.get("/data-collection/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert isinstance(data["uptime"], int)
        assert isinstance(data["event_count"], int)
        
        # Test unhealthy response
        mock_service.check_health.return_value = {
            "status": "error",
            "error": "Storage connection failed"
        }
        response = await async_client.get("/data-collection/health")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "error"
        assert "error" in data
    
    @pytest.mark.asyncio
    async def test_content_type_handling(self, async_client):
        """Test content type validation and handling."""
        # Test invalid content type
        response = await async_client.post(
            "/data-collection/events",
            content="invalid data",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422  # FastAPI handles invalid content type with validation error
        
        # Test missing content type
        response = await async_client.post(
            "/data-collection/events",
            content=b"invalid data"
        )
        assert response.status_code == 422  # FastAPI handles missing content type with validation error
        
        # Test valid JSON with wrong content type
        response = await async_client.post(
            "/data-collection/events",
            content=json.dumps(SAMPLE_EVENT.model_dump()),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422  # FastAPI handles wrong content type with validation error
