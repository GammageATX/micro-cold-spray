"""Communication service startup script."""

import os
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.communication.communication_app import create_communication_service, load_config


def main():
    """Run communication service."""
    try:
        # Get config from environment or use defaults
        host = os.getenv("COMMUNICATION_SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("COMMUNICATION_SERVICE_PORT", "8003"))
        reload = os.getenv("COMMUNICATION_SERVICE_RELOAD", "false").lower() == "true"
        
        # Create app instance with config
        app = create_communication_service()
        
        # Run service
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )

    except Exception as e:
        logger.exception(f"Failed to start communication service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
