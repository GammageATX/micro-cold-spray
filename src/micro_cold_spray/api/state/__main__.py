"""State service startup script."""

import os
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.state.state_app import create_state_service
from micro_cold_spray.utils.errors import create_error


def setup_logging():
    """Setup logging configuration.
    
    Creates log directory if it doesn't exist and configures console and file handlers.
    Console handler uses colored output while file handler includes rotation.
    """
    log_dir = os.path.join("logs", "state")
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
    logger.add(sys.stderr, format=log_format, level="INFO", enqueue=True)
    
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
        level="DEBUG",
        enqueue=True,
        compression="zip"
    )


def main():
    """Run state service.
    
    Configures logging, creates the FastAPI application, and starts the uvicorn server.
    Environment variables:
        STATE_SERVICE_HOST: Host to bind to (default: 0.0.0.0)
        STATE_SERVICE_PORT: Port to listen on (default: 8004)
        STATE_SERVICE_RELOAD: Enable auto-reload (default: false)
        STATE_SERVICE_LOG_LEVEL: Logging level (default: info)
    """
    try:
        # Setup logging
        setup_logging()
        logger.info("Starting state service...")

        # Create service
        app = create_state_service()
        
        # Get config from environment or use defaults
        host = os.getenv("STATE_SERVICE_HOST", "0.0.0.0")
        port = int(os.getenv("STATE_SERVICE_PORT", "8004"))
        reload = os.getenv("STATE_SERVICE_RELOAD", "false").lower() == "true"
        log_level = os.getenv("STATE_SERVICE_LOG_LEVEL", "info").lower()
        
        # Validate configuration
        if port < 1 or port > 65535:
            raise ValueError(f"Invalid port number: {port}")
            
        if log_level not in ["debug", "info", "warning", "error", "critical"]:
            raise ValueError(f"Invalid log level: {log_level}")
        
        # Log startup configuration
        logger.info("State service configuration:")
        logger.info(f"  Host: {host}")
        logger.info(f"  Port: {port}")
        logger.info(f"  Reload: {reload}")
        logger.info(f"  Log level: {log_level}")
        
        # Run service
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
            access_log=True
        )

    except Exception:
        logger.exception("Failed to start state service")
        sys.exit(1)


if __name__ == "__main__":
    main()
