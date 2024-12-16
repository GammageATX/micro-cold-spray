"""Tests for data collection router."""

from datetime import datetime
import json
import pytest
from unittest.mock import Mock, AsyncMock
from fastapi import FastAPI
from httpx import AsyncClient
import httpx

from micro_cold_spray.api.data_collection.router import init_router, get_service, router
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder for datetime objects."""
    def default(self, obj):
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
def mock_service():
    """Create a mock data collection service."""
    service = Mock(spec=DataCollectionService)
    service.is_running = True
    service.active_session = None
    service.start_collection = AsyncMock()
    service.stop_collection = AsyncMock()
    service.record_spray_event = AsyncMock()
    service.check_storage = AsyncMock(return_value=True)
    
    # Configure get_sequence_events to return empty list for valid sequence
    # and raise error for invalid sequence
    async def mock_get_events(sequence_id: str):
        if sequence_id == "invalid_sequence":
            raise DataCollectionError("Invalid sequence ID")
        if sequence_id == SAMPLE_EVENT.sequence_id:
            return [SAMPLE_EVENT]
        return []
    
    # Configure record_spray_event to raise error for invalid sequence
    async def mock_record_event(event: SprayEvent):
        if event.sequence_id == "invalid_sequence":
            raise DataCollectionError("Invalid sequence ID")
        return event
    
    service.get_sequence_events.side_effect = mock_get_events
    service.record_spray_event.side_effect = mock_record_event
    return service


@pytest.fixture
def app(mock_service):
    """Create test FastAPI application."""
    app = FastAPI()
    init_router(mock_service)
    app.include_router(router)
    return app


@pytest.fixture
async def async_client(app):
    """Create async test client."""
    async with AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        yield client


def test_init_router(mock_service):
    """Test router initialization."""
    init_router(mock_service)
    assert get_service() == mock_service


def test_get_service_not_initialized():
    """Test getting service when not initialized."""
    init_router(None)  # Reset service
    with pytest.raises(RuntimeError) as exc_info:
        get_service()
    assert "not initialized" in str(exc_info.value)


@pytest.mark.asyncio
async def test_start_collection(async_client, mock_service):
    """Test starting collection."""
    # Setup mock return value
    session = CollectionSession(
        sequence_id="test_sequence",
        start_time=datetime.now(),
        collection_params=COLLECTION_PARAMS
    )
    mock_service.start_collection.return_value = session
    
    # Test successful start
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": "test_sequence"},
        json=json.loads(json.dumps(COLLECTION_PARAMS, cls=DateTimeEncoder))
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert data["sequence_id"] == "test_sequence"
    
    mock_service.start_collection.assert_called_once_with(
        "test_sequence",
        COLLECTION_PARAMS
    )


@pytest.mark.asyncio
async def test_start_collection_invalid_sequence(async_client):
    """Test starting collection with invalid sequence ID."""
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": ""},
        json=json.loads(json.dumps(COLLECTION_PARAMS, cls=DateTimeEncoder))
    )
    assert response.status_code == 400
    assert "Invalid sequence ID" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_start_collection_error(async_client, mock_service):
    """Test starting collection with service error."""
    mock_service.start_collection.side_effect = DataCollectionError(
        "Collection already in progress"
    )
    
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": "test_sequence"},
        json=json.loads(json.dumps(COLLECTION_PARAMS, cls=DateTimeEncoder))
    )
    assert response.status_code == 400
    assert "Collection already in progress" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_stop_collection(async_client, mock_service):
    """Test stopping collection."""
    response = await async_client.post("/data-collection/stop")
    assert response.status_code == 200
    assert response.json()["status"] == "stopped"
    mock_service.stop_collection.assert_called_once()


@pytest.mark.asyncio
async def test_stop_collection_error(async_client, mock_service):
    """Test stopping collection with service error."""
    mock_service.stop_collection.side_effect = DataCollectionError(
        "No active collection"
    )
    
    response = await async_client.post("/data-collection/stop")
    assert response.status_code == 400
    assert "No active collection" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_record_event(async_client, mock_service):
    """Test recording spray event."""
    event = SprayEvent(
        id=None,
        sequence_id=SAMPLE_EVENT.sequence_id,
        spray_index=SAMPLE_EVENT.spray_index,
        timestamp=SAMPLE_EVENT.timestamp,
        x_pos=SAMPLE_EVENT.x_pos,
        y_pos=SAMPLE_EVENT.y_pos,
        z_pos=SAMPLE_EVENT.z_pos,
        pressure=SAMPLE_EVENT.pressure,
        temperature=SAMPLE_EVENT.temperature,
        flow_rate=SAMPLE_EVENT.flow_rate,
        status=SAMPLE_EVENT.status
    )
    
    # First validate sequence
    response = await async_client.get(f"/data-collection/events/{event.sequence_id}")
    assert response.status_code == 200
    
    # Then record event
    response = await async_client.post(
        "/data-collection/events",
        json=json.loads(event.model_dump_json())
    )
    print(f"Response: {response.status_code} - {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "recorded"
    assert data["sequence_id"] == event.sequence_id
    assert data["spray_index"] == event.spray_index


@pytest.mark.asyncio
async def test_record_event_invalid_sequence(async_client, mock_service):
    """Test recording event with invalid sequence ID."""
    # Try to get events for invalid sequence
    response = await async_client.get("/data-collection/events/invalid_sequence")
    assert response.status_code == 400
    
    # Then try to record event with invalid sequence
    event = SprayEvent(
        id=None,
        sequence_id="invalid_sequence",  # Invalid sequence
        spray_index=SAMPLE_EVENT.spray_index,
        timestamp=SAMPLE_EVENT.timestamp,
        x_pos=SAMPLE_EVENT.x_pos,
        y_pos=SAMPLE_EVENT.y_pos,
        z_pos=SAMPLE_EVENT.z_pos,
        pressure=SAMPLE_EVENT.pressure,
        temperature=SAMPLE_EVENT.temperature,
        flow_rate=SAMPLE_EVENT.flow_rate,
        status=SAMPLE_EVENT.status
    )
    
    response = await async_client.post(
        "/data-collection/events",
        json=json.loads(event.model_dump_json())
    )
    assert response.status_code == 400
    assert "Invalid sequence ID" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_record_event_error(async_client, mock_service):
    """Test recording event with service error."""
    mock_service.record_spray_event.side_effect = DataCollectionError(
        "No active collection session"
    )
    
    event = SprayEvent(
        id=None,
        sequence_id=SAMPLE_EVENT.sequence_id,
        spray_index=SAMPLE_EVENT.spray_index,
        timestamp=SAMPLE_EVENT.timestamp,
        x_pos=SAMPLE_EVENT.x_pos,
        y_pos=SAMPLE_EVENT.y_pos,
        z_pos=SAMPLE_EVENT.z_pos,
        pressure=SAMPLE_EVENT.pressure,
        temperature=SAMPLE_EVENT.temperature,
        flow_rate=SAMPLE_EVENT.flow_rate,
        status=SAMPLE_EVENT.status
    )
    
    # First validate sequence
    response = await async_client.get(f"/data-collection/events/{event.sequence_id}")
    assert response.status_code == 200
    
    # Then try to record event which should fail with service error
    response = await async_client.post(
        "/data-collection/events",
        json=json.loads(event.model_dump_json())
    )
    assert response.status_code == 400
    assert "No active collection session" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_get_events(async_client, mock_service):
    """Test retrieving sequence events."""
    response = await async_client.get(
        f"/data-collection/events/{SAMPLE_EVENT.sequence_id}"
    )
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 1
    assert events[0]["sequence_id"] == SAMPLE_EVENT.sequence_id


@pytest.mark.asyncio
async def test_get_events_invalid_sequence(async_client, mock_service):
    """Test retrieving events with invalid sequence ID."""
    mock_service.get_sequence_events.side_effect = DataCollectionError(
        "Sequence not found"
    )
    
    response = await async_client.get("/data-collection/events/invalid_sequence")
    assert response.status_code == 400
    assert "Sequence not found" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_get_events_error(async_client, mock_service):
    """Test retrieving events with service error."""
    mock_service.get_sequence_events.side_effect = DataCollectionError(
        "Failed to get events"
    )
    
    response = await async_client.get(
        f"/data-collection/events/{SAMPLE_EVENT.sequence_id}"
    )
    assert response.status_code == 400
    assert "Failed to get events" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_get_collection_status_active(async_client, mock_service):
    """Test getting collection status when active."""
    session = CollectionSession(
        sequence_id="test_sequence",
        start_time=datetime.now(),
        collection_params=COLLECTION_PARAMS
    )
    mock_service.active_session = session
    
    response = await async_client.get("/data-collection/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "active"
    assert data["sequence_id"] == session.sequence_id


@pytest.mark.asyncio
async def test_get_collection_status_inactive(async_client, mock_service):
    """Test getting collection status when inactive."""
    mock_service.active_session = None
    
    response = await async_client.get("/data-collection/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"


@pytest.mark.asyncio
async def test_get_collection_status_error(async_client, mock_service):
    """Test getting status with error."""
    mock_service.active_session = None
    mock_service.is_running = False
    mock_service.check_storage = AsyncMock(side_effect=Exception("Status error"))
    
    response = await async_client.get("/data-collection/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "inactive"
    assert "last_check" in data


@pytest.mark.asyncio
async def test_health_check_healthy(async_client, mock_service):
    """Test health check when healthy."""
    mock_service.check_storage.return_value = True
    mock_service.is_running = True
    
    response = await async_client.get("/data-collection/health")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "ok"
    assert data["storage"] == "ok"


@pytest.mark.asyncio
async def test_health_check_unhealthy(async_client, mock_service):
    """Test health check when unhealthy."""
    mock_service.check_storage.return_value = False
    mock_service.is_running = False
    
    response = await async_client.get("/data-collection/health")
    assert response.status_code == 503
    data = response.json()
    assert data["service"] == "error"
    assert data["storage"] == "error"


@pytest.mark.asyncio
async def test_health_check_error(async_client, mock_service):
    """Test health check with error."""
    mock_service.check_storage.side_effect = Exception("Health check error")
    
    response = await async_client.get("/data-collection/health")
    assert response.status_code == 503
    data = response.json()
    assert data["service"] == "error"
    assert data["storage"] == "error"
    assert "Health check error" in data["error"]


@pytest.mark.asyncio
async def test_start_collection_invalid_params(async_client):
    """Test starting collection with invalid parameters."""
    # Test negative interval
    invalid_params = {
        "mode": "continuous",
        "interval": -1.0,
        "duration": 60.0
    }
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": "test_sequence"},
        json=invalid_params
    )
    assert response.status_code == 400
    assert "Invalid collection parameters" in response.json()["detail"]["error"]

    # Test missing required parameter
    invalid_params = {
        "mode": "continuous",
        "duration": 60.0
        # Missing interval
    }
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": "test_sequence"},
        json=invalid_params
    )
    assert response.status_code == 400
    assert "Missing required parameter" in response.json()["detail"]["error"]


@pytest.mark.asyncio
async def test_record_event_invalid_data(async_client):
    """Test recording event with invalid data."""
    # Test invalid sensor values
    invalid_event = SAMPLE_EVENT.model_copy()
    invalid_event.pressure = -1.0  # Negative pressure
    
    response = await async_client.post(
        "/data-collection/events",
        json=json.loads(invalid_event.model_dump_json())
    )
    assert response.status_code == 422  # FastAPI's default validation error code
    assert "pressure must be positive" in response.json()["detail"][0]["msg"].lower()

    # Test malformed timestamp
    event_dict = json.loads(SAMPLE_EVENT.model_dump_json())
    event_dict["timestamp"] = "invalid-timestamp"
    
    response = await async_client.post(
        "/data-collection/events",
        json=event_dict
    )
    assert response.status_code == 422
    assert "invalid timestamp" in response.json()["detail"][0]["msg"].lower()


@pytest.mark.asyncio
async def test_sequence_management(async_client, mock_service):
    """Test sequence management edge cases."""
    # Test invalid sequence ID format
    response = await async_client.get("/data-collection/events/invalid%23sequence%40id")
    assert response.status_code == 400
    assert "Invalid sequence ID format" in response.json()["detail"]["error"]

    # Test concurrent sequence operations
    mock_service.start_collection.side_effect = DataCollectionError(
        "Another sequence is already active"
    )
    
    response = await async_client.post(
        "/data-collection/start",
        params={"sequence_id": "concurrent_sequence"},
        json=COLLECTION_PARAMS
    )
    assert response.status_code == 400
    assert "Another sequence is already active" in response.json()["detail"]["error"]
