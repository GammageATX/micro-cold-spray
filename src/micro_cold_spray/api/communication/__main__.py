"""Communication API entry point."""

import os
import uvicorn
from loguru import logger

from micro_cold_spray.api.communication.communication_app import create_app


def main():
    """Run communication API."""
    # Configure logging
    log_path = os.path.join(os.getcwd(), "logs", "communication.log")
    logger.add(
        log_path,
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )
    
    # Create and run app
    app = create_app()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8003,
        log_level="info"
    )


if __name__ == "__main__":
    main()
