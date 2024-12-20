"""Root test configuration and shared fixtures."""

import pytest
from datetime import datetime
import asyncio

from micro_cold_spray.api.base.base_service import BaseService


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for tests.
    
    This overrides pytest-asyncio's event_loop fixture to ensure
    we have a new loop for each test session.
    """
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_datetime(monkeypatch: pytest.MonkeyPatch) -> datetime:
    """Mock datetime for consistent timestamps."""
    FAKE_TIME = datetime(2023, 1, 1, 12, 0, 0)
    
    class MockDatetime:
        @classmethod
        def now(cls):
            return FAKE_TIME
            
    monkeypatch.setattr("datetime.datetime", MockDatetime)
    return FAKE_TIME
