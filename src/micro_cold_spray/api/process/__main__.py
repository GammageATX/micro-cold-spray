"""Process API entry point."""

import asyncio
import uvicorn
from loguru import logger

from micro_cold_spray.api.process.process_app import create_process_service


async def main():
    """Start process service."""
    try:
        # Create FastAPI app with process service
        app = create_process_service()
        
        # Run server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8001,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Failed to start process service: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
