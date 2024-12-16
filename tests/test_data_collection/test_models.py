"""Tests for data collection models."""

import pytest
from datetime import datetime, timezone
from typing import Dict, Any
from pydantic import ValidationError

from micro_cold_spray.api.data_collection.models import SprayEvent, CollectionSession
from . import TEST_SEQUENCE_ID, TEST_TIMESTAMP, TEST_COLLECTION_PARAMS


class TestSprayEvent:
    """Test SprayEvent model."""
    
    @pytest.fixture
    def valid_event_data(self) -> Dict[str, Any]:
        """Create valid event test data."""
        return {
            "sequence_id": TEST_SEQUENCE_ID,
            "spray_index": 1,
            "timestamp": TEST_TIMESTAMP,
            "x_pos": 10.0,
            "y_pos": 20.0,
            "z_pos": 30.0,
            "pressure": 100.0,
            "temperature": 25.0,
            "flow_rate": 5.0,
            "status": "active"
        }
    
    def test_spray_event_creation(self, valid_event_data: Dict[str, Any]) -> None:
        """Test creating spray event with valid data."""
        event = SprayEvent(**valid_event_data)
        
        # Verify all fields
        for field, value in valid_event_data.items():
            assert getattr(event, field) == value
    
    def test_spray_event_with_current_timestamp(self, valid_event_data: Dict[str, Any]) -> None:
        """Test creating event with current timestamp."""
        valid_event_data["timestamp"] = datetime.now(timezone.utc)
        event = SprayEvent(**valid_event_data)
        assert isinstance(event.timestamp, datetime)
    
    def test_spray_event_field_types(self, valid_event_data: Dict[str, Any]) -> None:
        """Test field type validation."""
        event = SprayEvent(**valid_event_data)
        assert isinstance(event.sequence_id, str)
        assert isinstance(event.spray_index, int)
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.x_pos, float)
        assert isinstance(event.y_pos, float)
        assert isinstance(event.z_pos, float)
        assert isinstance(event.pressure, float)
        assert isinstance(event.temperature, float)
        assert isinstance(event.flow_rate, float)
        assert isinstance(event.status, str)
    
    def test_spray_event_invalid_types(self, valid_event_data: Dict[str, Any]) -> None:
        """Test invalid field type handling."""
        # Test with invalid sequence_id type
        invalid_data = valid_event_data.copy()
        invalid_data["sequence_id"] = 123  # Should be string
        with pytest.raises(ValidationError) as exc_info:
            SprayEvent(**invalid_data)
        assert "Input should be a valid string" in str(exc_info.value)
        
        # Test with invalid spray_index type
        invalid_data = valid_event_data.copy()
        invalid_data["spray_index"] = "1"  # Should be int
        with pytest.raises(ValidationError) as exc_info:
            SprayEvent(**invalid_data)
        assert "Input should be a valid integer" in str(exc_info.value)
        
        # Test with invalid position type
        invalid_data = valid_event_data.copy()
        invalid_data["x_pos"] = "10.0"  # Should be float
        with pytest.raises(ValidationError) as exc_info:
            SprayEvent(**invalid_data)
        assert "Input should be a valid number" in str(exc_info.value)
    
    def test_spray_event_string_representation(self, valid_event_data: Dict[str, Any]) -> None:
        """Test string representation of event."""
        event = SprayEvent(**valid_event_data)
        str_repr = str(event)
        assert TEST_SEQUENCE_ID in str_repr
        assert str(event.spray_index) in str_repr
    
    def test_spray_event_equality(self, valid_event_data: Dict[str, Any]) -> None:
        """Test event equality comparison."""
        event1 = SprayEvent(**valid_event_data)
        event2 = SprayEvent(**valid_event_data)
        assert event1 == event2
        
        # Modified event should not be equal
        event2.spray_index = 999
        assert event1 != event2


class TestCollectionSession:
    """Test CollectionSession model."""
    
    @pytest.fixture
    def valid_session_data(self) -> Dict[str, Any]:
        """Create valid session test data."""
        return {
            "sequence_id": TEST_SEQUENCE_ID,
            "start_time": TEST_TIMESTAMP,
            "collection_params": TEST_COLLECTION_PARAMS
        }
    
    def test_collection_session_creation(self, valid_session_data: Dict[str, Any]) -> None:
        """Test creating collection session with valid data."""
        session = CollectionSession(**valid_session_data)
        
        # Verify basic fields
        assert session.sequence_id == TEST_SEQUENCE_ID
        assert session.start_time == TEST_TIMESTAMP
        assert session.collection_params == TEST_COLLECTION_PARAMS
        
        # Verify collection params
        assert session.collection_params["interval"] == 0.1
        assert session.collection_params["max_events"] == 100
        assert session.collection_params["buffer_size"] == 10
    
    def test_collection_session_field_types(self, valid_session_data: Dict[str, Any]) -> None:
        """Test field type validation."""
        session = CollectionSession(**valid_session_data)
        assert isinstance(session.sequence_id, str)
        assert isinstance(session.start_time, datetime)
        assert isinstance(session.collection_params, dict)
    
    def test_collection_session_invalid_types(self, valid_session_data: Dict[str, Any]) -> None:
        """Test invalid field type handling."""
        # Test with invalid sequence_id type
        invalid_data = valid_session_data.copy()
        invalid_data["sequence_id"] = 123  # Should be string
        with pytest.raises(ValidationError) as exc_info:
            CollectionSession(**invalid_data)
        assert "Input should be a valid string" in str(exc_info.value)
        
        # Test with invalid start_time type
        invalid_data = valid_session_data.copy()
        invalid_data["start_time"] = "2023-01-01"  # Should be datetime
        with pytest.raises(ValidationError) as exc_info:
            CollectionSession(**invalid_data)
        assert "Input should be a valid datetime" in str(exc_info.value)
        
        # Test with invalid collection_params type
        invalid_data = valid_session_data.copy()
        invalid_data["collection_params"] = [1, 2, 3]  # Should be dict
        with pytest.raises(ValidationError) as exc_info:
            CollectionSession(**invalid_data)
        assert "Input should be a valid dictionary" in str(exc_info.value)
    
    def test_collection_session_with_current_timestamp(self, valid_session_data: Dict[str, Any]) -> None:
        """Test creating session with current timestamp."""
        valid_session_data["start_time"] = datetime.now(timezone.utc)
        session = CollectionSession(**valid_session_data)
        assert isinstance(session.start_time, datetime)
    
    def test_collection_session_with_empty_params(self) -> None:
        """Test creating session with empty params."""
        session = CollectionSession(
            sequence_id=TEST_SEQUENCE_ID,
            start_time=TEST_TIMESTAMP,
            collection_params={}
        )
        assert isinstance(session.collection_params, dict)
        assert len(session.collection_params) == 0
    
    def test_collection_session_string_representation(self, valid_session_data: Dict[str, Any]) -> None:
        """Test string representation of session."""
        session = CollectionSession(**valid_session_data)
        str_repr = str(session)
        assert TEST_SEQUENCE_ID in str_repr
        assert session.start_time.isoformat() in str_repr
    
    def test_collection_session_equality(self, valid_session_data: Dict[str, Any]) -> None:
        """Test session equality comparison."""
        session1 = CollectionSession(**valid_session_data)
        session2 = CollectionSession(**valid_session_data)
        assert session1 == session2
        
        # Modified session should not be equal
        session2.sequence_id = "different_sequence"
        assert session1 != session2
