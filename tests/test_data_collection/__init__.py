"""Test package for data collection API."""

from datetime import datetime

# Common test data
TEST_SEQUENCE_ID = "test_sequence_001"
TEST_TIMESTAMP = datetime.now()

# Database configuration for tests
TEST_DB_CONFIG = {
    "dsn": "postgresql://test:test@localhost:5432/test_db"
}

# Common test parameters
TEST_COLLECTION_PARAMS = {
    "interval": 0.1,
    "max_events": 100,
    "buffer_size": 10
}

__all__ = [
    "TEST_SEQUENCE_ID",
    "TEST_TIMESTAMP",
    "TEST_DB_CONFIG",
    "TEST_COLLECTION_PARAMS"
]
