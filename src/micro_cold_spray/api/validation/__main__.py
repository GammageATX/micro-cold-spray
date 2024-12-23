"""Run validation service."""

import os
import sys
import uvicorn
from loguru import logger

from micro_cold_spray.api.validation import create_app


def main():
    """Run validation service."""
    try:
        # Configure logging
        logger.remove()  # Remove default handler
        logger.add(
            sys.stderr,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            level="INFO"
        )

        # Create and run app
        app = create_app()
        port = int(os.getenv("VALIDATION_PORT", "8007"))
        
        logger.info(f"Starting validation service on port {port}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )

    except Exception as e:
        logger.error(f"Failed to start validation service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
