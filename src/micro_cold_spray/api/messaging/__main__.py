"""Main entry point for messaging service."""

import asyncio
import uvicorn
from loguru import logger

from micro_cold_spray.api.messaging.messaging_app import MessagingApp


async def main():
    """Run the messaging service."""
    try:
        # Create and initialize app
        app = MessagingApp()
        
        # Start the service
        await app.startup()
        
        # Run the server
        config = uvicorn.Config(
            app=app,
            host="0.0.0.0",
            port=8004,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
        
    except Exception as e:
        logger.error(f"Failed to start messaging service: {e}")
        raise
    finally:
        # Ensure cleanup
        await app.shutdown()


if __name__ == "__main__":
    # Run the service
    asyncio.run(main())
