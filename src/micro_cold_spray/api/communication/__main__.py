"""Communication service startup script."""

import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.communication.communication_app import create_communication_service, load_config


def main():
    """Run communication service."""
    try:
        # Load config
        config = load_config()
        
        # Create app instance with config
        app = create_communication_service(config)
        
        # Run service using config values
        uvicorn.run(
            app,
            host=config["service"]["host"],
            port=config["service"]["port"],
            log_level=config["service"]["log_level"].lower()
        )

    except Exception as e:
        logger.exception(f"Failed to start communication service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
