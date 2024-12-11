# src/micro_cold_spray/__main__.py
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

# API imports
from micro_cold_spray.api.config import ConfigService, ConfigurationError
from micro_cold_spray.api.messaging import MessagingService
from micro_cold_spray.api.state import StateService
from micro_cold_spray.api.data_collection import DataCollectionService
from micro_cold_spray.api.communication import (
    PLCTagService,
    FeederTagService,
    TagCacheService
)

src_path = Path(__file__).parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))


def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.parent.parent


def setup_logging() -> None:
    """Configure loguru for application logging."""
    logger.remove()  # Remove default handler

    # Break up log format into smaller parts
    time_fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>"
    level_fmt = "<level>{level: <8}</level>"
    location_fmt = "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    message_fmt = "<level>{message}</level>"

    log_format = f"{time_fmt} | {level_fmt} | {location_fmt} - {message_fmt}"

    logger.add(
        sys.stderr,
        format=log_format,
        level="WARNING",
        enqueue=True  # Enable async logging
    )

    # Add file logging
    logger.add(
        "logs/micro_cold_spray.log",
        rotation="1 day",
        retention="30 days",
        compression="zip",
        level="DEBUG",
        enqueue=True
    )


def ensure_directories() -> None:
    """Ensure required directories exist."""
    project_root = get_project_root()
    directories = [
        "config",
        "data/parameters",
        "data/patterns",
        "data/sequences",
        "data/runs",
        "logs",
        "resources"
    ]

    for directory in directories:
        (project_root / directory).mkdir(parents=True, exist_ok=True)


async def initialize_system() -> tuple[
    ConfigService,
    MessagingService,
    PLCTagService,
    FeederTagService,
    StateService,
    DataCollectionService
]:
    """Initialize all system components."""
    logger.info("Starting system initialization")

    try:
        # Create message broker first
        logger.debug("Initializing MessageBroker")
        message_broker = MessagingService()
        await message_broker.initialize()

        # Create config manager with proper path and message broker
        logger.debug("Initializing ConfigManager")
        config_path = get_project_root() / "config"
        config_manager = ConfigService(config_path, message_broker)
        await config_manager.initialize()

        # Initialize tag cache service
        logger.debug("Initializing TagCacheService")
        tag_cache = TagCacheService()

        # Initialize communication services
        logger.debug("Initializing Communication Services")
        plc_service = PLCTagService(
            config_manager=config_manager,
            message_broker=message_broker,
            tag_cache=tag_cache
        )
        await plc_service.start()

        feeder_service = FeederTagService(
            config_manager=config_manager,
            message_broker=message_broker,
            tag_cache=tag_cache
        )
        await feeder_service.start()

        # Create and initialize state service
        logger.debug("Initializing StateService")
        state_service = StateService(
            config_manager=config_manager,
            message_broker=message_broker
        )
        await state_service.start()

        # Create and initialize data manager
        logger.debug("Initializing DataCollectionService")
        data_service = DataCollectionService(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await data_service.start()

        logger.info("System initialization complete")
        return (
            config_manager,
            message_broker,
            plc_service,
            feeder_service,
            state_service,
            data_service
        )

    except Exception as e:
        error_msg = {
            "error": str(e),
            "context": "system_initialization",
            "timestamp": datetime.now().isoformat()
        }
        logger.exception(f"Critical error during system initialization: {error_msg}")
        raise ConfigurationError("Failed to initialize system", error_msg) from e


async def main() -> None:
    """Application entry point with proper cleanup chains."""
    system_components = None

    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application - Service Mode")

        # Initialize system
        system_components = await initialize_system()
        (
            config_manager,
            message_broker,
            plc_service,
            feeder_service,
            state_service,
            data_service
        ) = system_components

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except Exception as e:
        error_msg = {
            "error": str(e),
            "context": "main_execution",
            "timestamp": datetime.now().isoformat()
        }
        logger.exception(f"Critical application error: {error_msg}")
        if 'message_broker' in locals() and message_broker:
            try:
                await message_broker.publish("error", error_msg)
            except Exception as publish_error:
                logger.error(f"Failed to publish error message: {publish_error}")
        raise
    finally:
        # Proper cleanup chain
        if system_components:
            (
                config_manager,
                message_broker,
                plc_service,
                feeder_service,
                state_service,
                data_service
            ) = system_components

            logger.info("Shutting down system components")
            try:
                await state_service.stop()
            except Exception as e:
                logger.error(f"Error shutting down state service: {e}")
            try:
                await plc_service.stop()
            except Exception as e:
                logger.error(f"Error shutting down plc service: {e}")
            try:
                await feeder_service.stop()
            except Exception as e:
                logger.error(f"Error shutting down feeder service: {e}")
            try:
                await data_service.stop()
            except Exception as e:
                logger.error(f"Error shutting down data service: {e}")
            try:
                await message_broker.stop()
            except Exception as e:
                logger.error(f"Error shutting down message broker: {e}")

        logger.info("Application shutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
