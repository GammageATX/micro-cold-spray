"""Script to start necessary services for tag communication."""

import asyncio
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.config.service import ConfigService
from micro_cold_spray.api.messaging.service import MessagingService
from micro_cold_spray.api.communication.service import CommunicationService


async def main():
    """Start required services."""
    try:
        # Initialize config service
        logger.info("Starting config service...")
        config_service = ConfigService()
        await config_service.start()
        logger.info("Config service started")

        # Initialize messaging service
        logger.info("Starting messaging service...")
        message_broker = MessagingService(config_service=config_service)
        await message_broker.start()
        logger.info("Messaging service started")

        # Initialize communication service
        logger.info("Starting communication service...")
        comm_service = CommunicationService(config_service=config_service)
        await comm_service.start()
        logger.info("Communication service started")

        # Start FastAPI server
        config = uvicorn.Config(
            "micro_cold_spray.api.communication.router:app",
            host="0.0.0.0",
            port=8002,
            reload=False,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    except Exception as e:
        logger.error(f"Error starting services: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
