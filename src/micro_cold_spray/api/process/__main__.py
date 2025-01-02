"""Process API entry point."""

import asyncio
import yaml
import uvicorn
from loguru import logger

from micro_cold_spray.api.process.process_app import create_process_service


async def main():
    """Start process service."""
    try:
        # Load config for service settings
        try:
            with open("config/process.yaml", "r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config, using defaults: {e}")
            config = {
                "service": {
                    "host": "0.0.0.0",
                    "port": 8004,
                    "log_level": "INFO"
                }
            }

        # Create FastAPI app with process service
        app = create_process_service()
        
        # Run server
        config = uvicorn.Config(
            app=app,
            host=config["service"]["host"],
            port=config["service"]["port"],
            log_level=config["service"]["log_level"].lower()
        )
        server = uvicorn.Server(config)
        await server.serve()

    except Exception as e:
        logger.error(f"Failed to start process service: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
