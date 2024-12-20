"""Root test configuration and shared fixtures."""

import pytest
import asyncio
from datetime import datetime
from typing import Generator


@pytest.fixture(scope="session")
def event_loop_policy() -> Generator[asyncio.AbstractEventLoopPolicy, None, None]:
    """Create event loop policy for Windows."""
    try:
        from asyncio import WindowsProactorEventLoopPolicy
        policy = WindowsProactorEventLoopPolicy()
        asyncio.set_event_loop_policy(policy)
        yield policy
    finally:
        asyncio.set_event_loop_policy(None)


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
