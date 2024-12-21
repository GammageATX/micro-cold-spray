"""Main entry point for data collection service."""

import os
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.data_collection.data_collection_app import DataCollectionApp


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
        os.path.join(log_dir, "data_collection.log"),
        rotation="1 day",
        retention="30 days",
        format=file_format,
        level="DEBUG"
    )


def main():
    """Run data collection service."""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting data collection service...")
        
        # Get config from environment or use defaults
        host = os.getenv("DATA_COLLECTION_HOST", "0.0.0.0")
        port = int(os.getenv("DATA_COLLECTION_PORT", "8005"))  # Default port for data collection
        reload = os.getenv("DATA_COLLECTION_RELOAD", "false").lower() == "true"
        
        # Log startup configuration
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Reload: {reload}")
        
        # Run service
        uvicorn.run(
            "micro_cold_spray.api.data_collection.data_collection_app:DataCollectionApp",
            host=host,
            port=port,
            reload=reload,
            log_level="info",
            factory=True
        )

    except Exception as e:
        logger.error(f"Failed to start data collection service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
