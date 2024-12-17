import pytest
import asyncio
from micro_cold_spray.__main__ import get_test_config
import uvicorn


@pytest.fixture(scope="function")
def event_loop_policy():
    """Create and set a new event loop policy for each test."""
    policy = asyncio.get_event_loop_policy()
    return policy


@pytest.fixture(scope="function")
async def config_service():
    """Start a test config service instance."""
    config = get_test_config('config')
    server = uvicorn.Server(config)
    
    # Start server in background
    server_task = asyncio.create_task(server.serve())
    await asyncio.sleep(1)  # Give server time to start
    
    yield f"http://127.0.0.1:{config.port}"
    
    # Cleanup
    server.should_exit = True
    await server_task
