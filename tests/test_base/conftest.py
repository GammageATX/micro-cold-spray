"""Base-specific test fixtures."""

import pytest
from typing import AsyncGenerator, Generator
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
import httpx

# Import base-specific fixtures
from ..fixtures.base import base_service, test_app, test_app_with_cors  # noqa: F401

# Import shared fixtures
from ..conftest import (  # noqa: F401
    async_client,
    test_client,
    mock_base_service,
    mock_app,
    setup_logging,
    mock_datetime
)

# Use loop_scope instead of scope
pytestmark = pytest.mark.asyncio(loop_scope="session")
