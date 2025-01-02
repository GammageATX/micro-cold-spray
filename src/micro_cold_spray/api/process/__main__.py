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
                "version": "1.0.0",
                "mode": "normal",
                "host": "0.0.0.0",
                "port": 8004,
                "log_level": "INFO",
                "components": {
                    "pattern": {"version": "1.0.0"},
                    "parameter": {"version": "1.0.0"},
                    "sequence": {"version": "1.0.0"},
                    "schema": {"version": "1.0.0"}
                }
            }

        # Create FastAPI app with process service
        app = create_process_service()
        
        # Run server
        config = uvicorn.Config(
            app=app,
            host=config.get("host", "0.0.0.0"),
            port=config.get("port", 8004),
            log_level=config.get("log_level", "info").lower()
        )
        server = uvicorn.Server(config)
        await server.serve()

    except Exception as e:
        logger.error(f"Failed to start process service: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
