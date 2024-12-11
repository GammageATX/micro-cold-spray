# src/micro_cold_spray/__main__.py
import asyncio
import sys
from datetime import datetime
from pathlib import Path
import subprocess
from multiprocessing import Process

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
from micro_cold_spray.ui.router import app as ui_app
import uvicorn

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


async def run_ui():
    """Run the UI service."""
    config = uvicorn.Config(ui_app, host="0.0.0.0", port=8000, reload=True)
    server = uvicorn.Server(config)
    await server.serve()


# Service definitions
SERVICES = {
    "config": 8001,
    "communication": 8002,
    "process": 8003,
    "state": 8004,
    "data_collection": 8005,
    "validation": 8006,
    "messaging": 8007
}


class ServiceManager:
    """Manages API service processes."""
    
    def __init__(self):
        self.processes = {}
        
    def start_service(self, name: str, port: int):
        """Start a service process."""
        try:
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    f"micro_cold_spray.api.{name}.router:app",
                    "--host", "0.0.0.0",
                    "--port", str(port),
                    "--reload"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = process
            
            if process.poll() is not None:
                error = process.stderr.read()
                logger.error(f"Service {name} failed to start: {error}")
                return None
                
            logger.info(f"Started {name} service on port {port}")
            return process
        except Exception as e:
            logger.error(f"Failed to start {name} service: {e}")
            return None

    async def start_all(self):
        """Start all API services."""
        logger.info("Starting all services...")
        for name, port in SERVICES.items():
            if self.start_service(name, port) is None:
                logger.error(f"Failed to start {name} service")
                await self.stop_all()
                sys.exit(1)

    async def stop_all(self):
        """Stop all running services."""
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                logger.info(f"Stopped {name} service")
            except subprocess.TimeoutExpired:
                process.kill()
                logger.warning(f"Killed {name} service")
            except Exception as e:
                logger.error(f"Error stopping {name} service: {e}")


async def main():
    """Application entry point with proper cleanup chains."""
    service_manager = ServiceManager()

    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")

        # Start all services
        await service_manager.start_all()

        # Initialize system
        system_components = await initialize_system()
        
        # Start UI
        logger.info("Starting UI service")
        ui_process = Process(target=lambda: asyncio.run(run_ui()))
        ui_process.start()

        # Keep running until interrupted
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutdown requested...")
    except Exception as e:
        error_msg = {
            "error": str(e),
            "context": "main_execution",
            "timestamp": datetime.now().isoformat()
        }
        logger.exception(f"Critical application error: {error_msg}")
        raise
    finally:
        if 'ui_process' in locals():
            ui_process.terminate()
            ui_process.join()
        await service_manager.stop_all()
        logger.info("Application shutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
