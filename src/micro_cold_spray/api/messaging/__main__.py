"""Main entry point for messaging service."""

import asyncio
import uvicorn
from loguru import logger

from micro_cold_spray.api.messaging.messaging_app import MessagingApp


async def main():
    """Run messaging service."""
    try:
        # Create app
        app = MessagingApp(
            title="Messaging Service",
            description="Service for handling pub/sub messaging",
            version="1.0.0"
        )
        
        # Run server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8004,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Failed to run messaging service: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
