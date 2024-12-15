import pytest
import asyncio
from micro_cold_spray.__main__ import get_test_config
import uvicorn


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
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
