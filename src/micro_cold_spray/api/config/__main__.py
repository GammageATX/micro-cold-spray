"""Configuration service startup script."""

import os
import sys
import uvicorn
from loguru import logger
from fastapi import FastAPI

from micro_cold_spray.api.config.config_service import create_config_service


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
        os.path.join(log_dir, "config_service.log"),
        rotation="1 day",
        retention="30 days",
        format=file_format,
        level="DEBUG"
    )


def main():
    """Run configuration service."""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting configuration service...")

        # Create service
        app = create_config_service()
        
        # Get config from environment or use defaults
        host = os.getenv("CONFIG_SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("CONFIG_SERVICE_PORT", "8001"))
        reload = os.getenv("CONFIG_SERVICE_RELOAD", "false").lower() == "true"
        
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
        logger.exception(f"Failed to start configuration service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
