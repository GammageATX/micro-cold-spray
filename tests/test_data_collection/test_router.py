"""Tests for data collection router."""

import pytest
from unittest.mock import AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

from micro_cold_spray.api.data_collection.router import router, init_router
from micro_cold_spray.api.data_collection.service import DataCollectionService
from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
from micro_cold_spray.api.data_collection.exceptions import DataCollectionError
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_COLLECTION_PARAMS


class TestDataCollectionRouter:
    """Test data collection router endpoints."""
    
    @pytest.fixture
    def mock_service(self) -> AsyncMock:
        """Create mock service."""
        mock = AsyncMock(spec=DataCollectionService)
        mock.is_running = True
        mock.active_session = None
        mock.check_storage = AsyncMock(return_value=True)
        return mock
        
    @pytest.fixture
    def test_client(self, mock_service: AsyncMock) -> TestClient:
        """Create test client."""
        app = FastAPI()
        app.include_router(router)
        init_router(mock_service)
        return TestClient(app)
    
    @pytest.mark.asyncio
    async def test_start_collection_endpoint(self, test_client: TestClient, mock_service: AsyncMock) -> None:
        """Test start collection endpoint."""
        # Test successful start
        mock_service.start_collection.return_value = CollectionSession(
            sequence_id=TEST_SEQUENCE_ID,
            start_time=TEST_TIMESTAMP,
            collection_params=TEST_COLLECTION_PARAMS
        )
        
        response = test_client.post(
            "/data-collection/start",
            params={"sequence_id": TEST_SEQUENCE_ID},
            json=TEST_COLLECTION_PARAMS
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "started"
        assert data["sequence_id"] == TEST_SEQUENCE_ID
        
        # Test invalid sequence ID
        response = test_client.post(
            "/data-collection/start",
            params={"sequence_id": ""},
            json=TEST_COLLECTION_PARAMS
        )
        assert response.status_code == 400
        assert "Invalid sequence ID" in response.json()["detail"]["error"]
        
        # Test service error
        mock_service.start_collection.side_effect = DataCollectionError("Test error")
        response = test_client.post(
            "/data-collection/start",
            params={"sequence_id": TEST_SEQUENCE_ID},
            json=TEST_COLLECTION_PARAMS
        )
        assert response.status_code == 400
        assert "Test error" in response.json()["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_stop_collection_endpoint(self, test_client: TestClient, mock_service: AsyncMock) -> None:
        """Test stop collection endpoint."""
        # Test successful stop
        response = test_client.post("/data-collection/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
        mock_service.stop_collection.assert_called_once()
        
        # Test service error
        mock_service.stop_collection.side_effect = DataCollectionError("No active session")
        response = test_client.post("/data-collection/stop")
        assert response.status_code == 400
        assert "No active session" in response.json()["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_record_event_endpoint(self, test_client: TestClient, mock_service: AsyncMock) -> None:
        """Test record event endpoint."""
        event = SprayEvent(
            sequence_id=TEST_SEQUENCE_ID,
            spray_index=1,
            timestamp=TEST_TIMESTAMP,
            x_pos=10.0,
            y_pos=20.0,
            z_pos=30.0,
            pressure=100.0,
            temperature=25.0,
            flow_rate=5.0,
            status="active"
        )
        
        # Test successful record
        response = test_client.post("/data-collection/events", json=event.__dict__)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "recorded"
        assert data["sequence_id"] == TEST_SEQUENCE_ID
        assert data["spray_index"] == 1
        
        # Test invalid event data
        invalid_event = event.__dict__.copy()
        invalid_event["pressure"] = "invalid"
        response = test_client.post("/data-collection/events", json=invalid_event)
        assert response.status_code == 422  # Validation error
        
        # Test service error
        mock_service.record_spray_event.side_effect = DataCollectionError("Test error")
        response = test_client.post("/data-collection/events", json=event.__dict__)
        assert response.status_code == 400
        assert "Test error" in response.json()["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_get_events_endpoint(self, test_client: TestClient, mock_service: AsyncMock) -> None:
        """Test get events endpoint."""
        # Setup mock events
        events = [
            SprayEvent(
                sequence_id=TEST_SEQUENCE_ID,
                spray_index=i,
                timestamp=TEST_TIMESTAMP,
                x_pos=float(i),
                y_pos=float(i),
                z_pos=float(i),
                pressure=100.0,
                temperature=25.0,
                flow_rate=5.0,
                status="active"
            ).__dict__
            for i in range(3)
        ]
        mock_service.get_sequence_events.return_value = events
        
        # Test successful retrieval
        response = test_client.get(f"/data-collection/events/{TEST_SEQUENCE_ID}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all(e["sequence_id"] == TEST_SEQUENCE_ID for e in data)
        
        # Test invalid sequence ID
        response = test_client.get("/data-collection/events/")
        assert response.status_code == 404
        
        # Test service error
        mock_service.get_sequence_events.side_effect = DataCollectionError("Test error")
        response = test_client.get(f"/data-collection/events/{TEST_SEQUENCE_ID}")
        assert response.status_code == 400
        assert "Test error" in response.json()["detail"]["error"]
    
    @pytest.mark.asyncio
    async def test_health_check_endpoint(self, test_client: TestClient, mock_service: AsyncMock) -> None:
        """Test health check endpoint."""
        # Test healthy service
        response = test_client.get("/data-collection/health")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "ok"
        assert data["storage"] == "ok"
        
        # Test unhealthy storage
        mock_service.check_storage.return_value = False
        response = test_client.get("/data-collection/health")
        assert response.status_code == 503
        data = response.json()
        assert data["storage"] == "error"
        
        # Test service error
        mock_service.check_storage.side_effect = Exception("Test error")
        response = test_client.get("/data-collection/health")
        assert response.status_code == 503
        data = response.json()
        assert data["service"] == "error"
        assert data["storage"] == "error"
        assert "Test error" in data["error"]
