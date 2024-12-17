"""Tests for data collection router."""

from datetime import datetime, timezone
import json
from typing import AsyncGenerator
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient
import httpx
from fastapi.encoders import jsonable_encoder

from micro_cold_spray.api.data_collection.router import router
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
    service.initialize = AsyncMock()
    service.start = AsyncMock()
    service.stop = AsyncMock()
    service._initialized = True  # Mark service as initialized
    
    # Configure default behavior
    service.check_health.return_value = {"status": "ok"}
    service.start_collection.side_effect = lambda seq_id, params: CollectionSession(
        sequence_id=seq_id,
        start_time=datetime.now(timezone.utc),
        collection_params=params
    )
    
    return service


@pytest.fixture
def app(mock_service: Mock) -> FastAPI:
    """Create test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    
    # Initialize router with mock service
    from micro_cold_spray.api.data_collection.router import init_router
    init_router(mock_service)
    
    # Configure JSON encoder for datetime
    app.json_encoder = DateTimeEncoder
    return app


@pytest.fixture
async def async_client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    transport = httpx.ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Content-Type": "application/json"}
    ) as client:
        # Patch the client's build_request method to handle datetime serialization
        original_build_request = client.build_request
        
        def patched_build_request(method: str, url: str, **kwargs):
            if "json" in kwargs:
                kwargs["content"] = json.dumps(kwargs.pop("json"), cls=DateTimeEncoder).encode()
            return original_build_request(method, url, **kwargs)
        
        client.build_request = patched_build_request
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
        response = await async_client.post("/data-collection/start", json={"collection_params": {}})
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # FastAPI validation error format
        
        # Test invalid characters in sequence ID
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "invalid#sequence@id"},
            json={"collection_params": {}}
        )
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # FastAPI validation error format
        
        # Test sequence ID length limits
        long_id = "a" * 101
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": long_id},
            json={"collection_params": {}}
        )
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)  # FastAPI validation error format
    
    @pytest.mark.asyncio
    async def test_collection_params_validation(self, async_client, mock_service):
        """Test collection parameters validation."""
        # Test missing required params
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json={}
        )
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
        
        # Test invalid parameter types
        invalid_params = {
            "interval": "invalid",
            "duration": -1
        }
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=invalid_params
        )
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
        
        # Test parameter range validation
        invalid_ranges = {
            "interval": 0.0,
            "duration": -1.0
        }
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=invalid_ranges
        )
        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
    
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
            start_time=datetime.now(timezone.utc),
            collection_params=COLLECTION_PARAMS
        )
        mock_service.start_collection.return_value = session
        
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
        # Test service error - Collection already in progress
        error_msg = "Collection already in progress"
        mock_service.start_collection.side_effect = DataCollectionError(error_msg)
        
        response = await async_client.post(
            "/data-collection/start",
            params={"sequence_id": "test_sequence"},
            json=COLLECTION_PARAMS
        )
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        assert "error" in data["detail"]
        assert error_msg in str(data["detail"]["error"])
        
        # Test service error - No active session
        error_msg = "No active collection session"
        mock_service.record_spray_event.side_effect = DataCollectionError(error_msg)
        
        response = await async_client.post(
            "/data-collection/events",
            json=SAMPLE_EVENT.model_dump()
        )
        assert response.status_code == 404  # Not Found
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        assert "error" in data["detail"]
        assert error_msg in str(data["detail"]["error"])
        
        # Test service error - Duplicate event
        error_msg = "Duplicate spray event"
        mock_service.record_spray_event.side_effect = DataCollectionError(error_msg)
        
        response = await async_client.post(
            "/data-collection/events",
            json=SAMPLE_EVENT.model_dump()
        )
        assert response.status_code == 409  # Conflict
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        assert "error" in data["detail"]
        assert error_msg in str(data["detail"]["error"])
        
        # Test validation error response
        response = await async_client.post(
            "/data-collection/events",
            json={"invalid": "data"}
        )
        assert response.status_code == 422  # Unprocessable Entity
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
        
        # Test internal server error
        error_msg = "Internal server error"
        mock_service.record_spray_event.side_effect = Exception(error_msg)
        
        response = await async_client.post(
            "/data-collection/events",
            json=SAMPLE_EVENT.model_dump()
        )
        assert response.status_code == 500  # Internal Server Error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], dict)
        assert "error" in data["detail"]
        assert error_msg in str(data["detail"]["message"])
    
    @pytest.mark.asyncio
    async def test_health_check_response(self, async_client, mock_service):
        """Test health check response format."""
        # Test healthy response
        mock_service.is_running = True
        mock_service.check_storage.return_value = True
        response = await async_client.get("/data-collection/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ok"
        assert data["storage"] == "ok"
        
        # Test unhealthy response
        mock_service.is_running = False
        mock_service.check_storage.return_value = False
        response = await async_client.get("/data-collection/health")
        assert response.status_code == 503
        data = response.json()
        assert data["service"] == "error"
        assert data["storage"] == "error"
    
    @pytest.mark.asyncio
    async def test_content_type_handling(self, async_client, mock_service):
        """Test content type validation and handling."""
        # Test invalid content type
        response = await async_client.post(
            "/data-collection/events",
            content="invalid data",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422  # FastAPI handles invalid content type with validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
        
        # Test missing content type
        response = await async_client.post(
            "/data-collection/events",
            content=b"invalid data"
        )
        assert response.status_code == 422  # FastAPI handles missing content type with validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
        
        # Test valid JSON with wrong content type
        event_data = SAMPLE_EVENT.model_dump()
        event_data["timestamp"] = event_data["timestamp"].isoformat()  # Convert datetime to string
        response = await async_client.post(
            "/data-collection/events",
            content=json.dumps(event_data),
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        assert response.status_code == 422  # FastAPI handles wrong content type with validation error
        data = response.json()
        assert "detail" in data
        assert isinstance(data["detail"], list)
        assert any("msg" in error for error in data["detail"])  # FastAPI validation error format
