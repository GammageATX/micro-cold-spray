"""Main entry point for data collection service."""

import os
import sys
import yaml
import uvicorn
from loguru import logger

from micro_cold_spray.api.data_collection.data_collection_app import create_data_collection_app
from micro_cold_spray.utils.errors import create_error


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


def load_config():
    """Load service configuration."""
    try:
        config_path = os.path.join("config", "data_collection.yaml")
        if not os.path.exists(config_path):
            logger.warning(f"Config file not found at {config_path}, using defaults")
            return {
                "service": {
                    "version": "1.0.0",
                    "host": "0.0.0.0",
                    "port": 8006,
                    "history_retention_days": 30
                }
            }

        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        raise create_error(
            status_code=500,
            message=f"Failed to load configuration: {str(e)}"
        )


def main():
    """Run data collection service."""
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting data collection service...")
        
        # Load config
        config = load_config()
        service_config = config.get("service", {})
        
        # Get config from environment or use defaults
        host = os.getenv("DATA_COLLECTION_HOST", service_config.get("host", "0.0.0.0"))
        port = int(os.getenv("DATA_COLLECTION_PORT", service_config.get("port", 8006)))
        reload = os.getenv("DATA_COLLECTION_RELOAD", "false").lower() == "true"
        
        # Log startup configuration
        logger.info(f"Host: {host}")
        logger.info(f"Port: {port}")
        logger.info(f"Reload: {reload}")
        
        # Run service
        uvicorn.run(
            "micro_cold_spray.api.data_collection.data_collection_app:create_data_collection_app",
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
