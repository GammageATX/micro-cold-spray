"""State service startup script."""

import os
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.state.state_app import create_state_service


def setup_logging():
    """Setup logging configuration."""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Remove default handler
    logger.remove()
    
    # Add console handler with color
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, format=log_format, level="INFO")
    
    # Add file handler with rotation
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level: <8} | "
        "{name}:{function}:{line} - "
        "{message}"
    )
    logger.add(
        os.path.join(log_dir, "state_service.log"),
        rotation="1 day",
        retention="30 days",
        format=file_format,
        level="DEBUG"
    )


def main():
    """Run state service."""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting state service...")

        # Create service
        app = create_state_service()
        
        # Get config from environment or use defaults
        host = os.getenv("STATE_SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("STATE_SERVICE_PORT", "8004"))  # Default port for state service
        reload = os.getenv("STATE_SERVICE_RELOAD", "false").lower() == "true"
        
        # Log startup configuration
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Reload: {reload}")
        
        # Run service
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level="info"
        )

    except Exception as e:
        logger.exception(f"Failed to start state service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
