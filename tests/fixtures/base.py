"""Base test fixtures."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests.conftest import MockBaseService


@pytest.fixture
def test_app():
    """Create test app fixture."""
    app = FastAPI()
    return app


@pytest.fixture
def test_client(test_app):
    """Create test client fixture."""
    return TestClient(test_app)
