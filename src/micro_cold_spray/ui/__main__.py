"""Main entry point for the UI service."""

import os
import sys
from pathlib import Path

import uvicorn
from loguru import logger

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


def setup_logging() -> None:
    """Configure logging for the UI service."""
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    # Remove default logger
    logger.remove()

    # Add console logger with custom format
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        colorize=True
    )

    # Add file logger
    logs_dir = PROJECT_ROOT / "logs" / "ui"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "ui.log"

    logger.add(
        str(log_file),
        format=log_format,
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )


def get_server_config() -> dict:
    """Get server configuration from environment variables."""
    return {
        "host": os.getenv("UI_HOST", "127.0.0.1"),
        "port": int(os.getenv("UI_PORT", "8000")),
        "reload": os.getenv("UI_RELOAD", "false").lower() == "true"
    }


def start_server(config: dict) -> None:
    """Start the uvicorn server with the given configuration."""
    try:
        uvicorn.run(
            "micro_cold_spray.ui.app:app",
            host=config["host"],
            port=config["port"],
            reload=config["reload"],
            log_level="info",
            access_log=True
        )
    except Exception as e:
        logger.error(f"Failed to start UI service: {e}")
        sys.exit(1)


def main() -> None:
    """Start the UI service."""
    # Configure logging
    setup_logging()
    logger.info("Starting UI service...")

    # Get server configuration
    config = get_server_config()

    # Log startup configuration
    logger.info(f"Host: {config['host']}")
    logger.info(f"Port: {config['port']}")
    logger.info(f"Reload: {config['reload']}")

    # Start server
    start_server(config)


if __name__ == "__main__":
    main()
