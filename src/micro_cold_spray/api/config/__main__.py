"""Configuration service startup script."""

import sys
import yaml
import uvicorn
from loguru import logger


def main():
    """Run configuration service."""
    try:
        # Load config for service settings
        try:
            with open("config/config.yaml", "r") as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config, using defaults: {e}")
            config = {
                "service": {
                    "host": "0.0.0.0",
                    "port": 8001,
                    "log_level": "INFO"
                }
            }
        
        # Import here to avoid circular imports
        from micro_cold_spray.api.config.config_app import create_config_service
        
        # Create app instance
        app = create_config_service()
        
        # Run service using config values
        uvicorn.run(
            app,
            host=config["service"]["host"],
            port=config["service"]["port"],
            log_level=config["service"]["log_level"].lower()
        )

    except Exception as e:
        logger.exception(f"Failed to start configuration service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
