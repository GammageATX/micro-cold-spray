# src/micro_cold_spray/__main__.py
import os
import sys
import time
import signal
from pathlib import Path
from typing import Dict, Any, Set
import multiprocessing as mp
from enum import Enum
import requests
from requests.exceptions import RequestException

import uvicorn
from loguru import logger

# Add project root to Python path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.append(str(PROJECT_ROOT))


class ServiceStatus(Enum):
    """Service status enumeration."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    FAILED = "failed"
    STOPPING = "stopping"


class Service:
    """Service configuration and status tracking."""
    def __init__(
        self,
        name: str,
        module: str,
        host: str,
        port: int,
        dependencies: Set[str] = None,
        health_endpoint: str = "/health",
        startup_timeout: int = 30
    ):
        self.name = name
        self.module = module
        self.host = host
        self.port = port
        self.dependencies = dependencies or set()
        self.health_endpoint = health_endpoint
        self.startup_timeout = startup_timeout
        self.status = ServiceStatus.STOPPED
        self.process = None
        self.start_time = None

    @property
    def url(self) -> str:
        """Get the base URL for the service."""
        return f"http://{self.host}:{self.port}"

    def check_health(self) -> bool:
        """Check if the service is healthy."""
        try:
            response = requests.get(f"{self.url}{self.health_endpoint}", timeout=5)
            return response.status_code == 200
        except RequestException:
            return False


def get_service_config(service_name: str) -> Dict[str, Any]:
    """Get configuration for a service from environment variables."""
    return {
        "host": os.getenv(f"{service_name.upper()}_HOST", "127.0.0.1"),
        "port": int(os.getenv(f"{service_name.upper()}_PORT", "8000")),
        "reload": os.getenv(f"{service_name.upper()}_RELOAD", "false").lower() == "true"
    }


class ServiceManager:
    """Manages service lifecycle and dependencies."""
    def __init__(self):
        self.services: Dict[str, Service] = {}
        self._setup_services()
        self.running = True
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _setup_services(self):
        """Initialize service configurations."""
        # Config service (no dependencies)
        config_cfg = get_service_config("config")
        self.services["config"] = Service(
            name="config",
            module="micro_cold_spray.core.config.app:app",
            host=config_cfg["host"],
            port=config_cfg["port"],
            dependencies=set()
        )

        # Communication service (depends on config)
        comm_cfg = get_service_config("communication")
        self.services["communication"] = Service(
            name="communication",
            module="micro_cold_spray.core.communication.app:app",
            host=comm_cfg["host"],
            port=comm_cfg["port"],
            dependencies={"config"}
        )

        # Process service (depends on config and communication)
        process_cfg = get_service_config("process")
        self.services["process"] = Service(
            name="process",
            module="micro_cold_spray.core.process.app:app",
            host=process_cfg["host"],
            port=process_cfg["port"],
            dependencies={"config", "communication"}
        )

        # Data Collection service
        dc_cfg = get_service_config("datacollection")
        self.services["datacollection"] = Service(
            name="datacollection",
            module="micro_cold_spray.core.datacollection.app:app",
            host=dc_cfg["host"],
            port=dc_cfg["port"],
            dependencies={"config", "communication"}
        )

        # Validation service
        validation_cfg = get_service_config("validation")
        self.services["validation"] = Service(
            name="validation",
            module="micro_cold_spray.core.validation.app:app",
            host=validation_cfg["host"],
            port=validation_cfg["port"],
            dependencies={"config"}
        )

        # Tag service
        tag_cfg = get_service_config("tag")
        self.services["tag"] = Service(
            name="tag",
            module="micro_cold_spray.core.tag.app:app",
            host=tag_cfg["host"],
            port=tag_cfg["port"],
            dependencies={"config"}
        )

        # UI service (depends on all other services)
        ui_cfg = get_service_config("ui")
        self.services["ui"] = Service(
            name="ui",
            module="micro_cold_spray.ui.app:app",
            host=ui_cfg["host"],
            port=ui_cfg["port"],
            dependencies={"config", "communication", "process", "datacollection", "validation", "tag"}
        )

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}")
        self.running = False
        self.stop_all_services()

    def start_service(self, service_name: str) -> bool:
        """Start a service and wait for it to be healthy."""
        service = self.services[service_name]
        
        # Check dependencies
        for dep in service.dependencies:
            if self.services[dep].status != ServiceStatus.RUNNING:
                logger.warning(f"Cannot start {service_name}: dependency {dep} not running")
                return False

        try:
            logger.info(f"Starting {service_name} service...")
            service.status = ServiceStatus.STARTING
            service.start_time = time.time()

            service.process = mp.Process(
                target=uvicorn.run,
                kwargs={
                    "app": service.module,
                    "host": service.host,
                    "port": service.port,
                    "log_level": "info",
                    "access_log": True
                }
            )
            service.process.start()

            # Wait for service to be healthy
            start_time = time.time()
            while time.time() - start_time < service.startup_timeout:
                if service.check_health():
                    service.status = ServiceStatus.RUNNING
                    logger.info(f"{service_name} service is healthy")
                    return True
                time.sleep(1)

            service.status = ServiceStatus.FAILED
            logger.error(f"{service_name} service failed to start")
            return False

        except Exception as e:
            logger.error(f"Failed to start {service_name} service: {e}")
            service.status = ServiceStatus.FAILED
            return False

    def stop_service(self, service_name: str) -> None:
        """Stop a service gracefully."""
        service = self.services[service_name]
        if service.process and service.process.is_alive():
            logger.info(f"Stopping {service_name} service...")
            service.status = ServiceStatus.STOPPING
            service.process.terminate()
            service.process.join(timeout=5)
            if service.process.is_alive():
                service.process.kill()
            service.status = ServiceStatus.STOPPED
            logger.info(f"{service_name} service stopped")

    def start_all_services(self) -> None:
        """Start all services in dependency order."""
        # Start services without dependencies first
        started = set()
        while len(started) < len(self.services):
            for name, service in self.services.items():
                if name in started:
                    continue
                if service.dependencies.issubset(started):
                    if self.start_service(name):
                        started.add(name)
                    else:
                        logger.error(f"Failed to start {name} service")
                        self.stop_all_services()
                        return

    def stop_all_services(self) -> None:
        """Stop all services in reverse dependency order."""
        # Stop services in reverse order of dependencies
        stopped = set()
        while len(stopped) < len(self.services):
            for name, service in self.services.items():
                if name in stopped:
                    continue
                # Only stop if all dependent services are stopped
                can_stop = True
                for other_service in self.services.values():
                    if name in other_service.dependencies and other_service.name not in stopped:
                        can_stop = False
                        break
                if can_stop:
                    self.stop_service(name)
                    stopped.add(name)

    def monitor_services(self) -> None:
        """Monitor service health and restart failed services."""
        while self.running:
            for name, service in self.services.items():
                if service.status == ServiceStatus.RUNNING and not service.check_health():
                    logger.warning(f"{name} service is unhealthy, attempting restart")
                    self.stop_service(name)
                    self.start_service(name)
            time.sleep(5)


def setup_logging() -> None:
    """Configure logging for all services."""
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
    logs_dir = PROJECT_ROOT / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / "mcs.log"

    logger.add(
        str(log_file),
        format=log_format,
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )


def main() -> None:
    """Start the Micro Cold Spray system."""
    # Configure logging
    setup_logging()
    logger.info("Starting Micro Cold Spray system...")

    # Initialize and start service manager
    service_manager = ServiceManager()
    
    try:
        # Start all services
        service_manager.start_all_services()
        
        # Monitor services in the main thread
        service_manager.monitor_services()
    
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        service_manager.stop_all_services()


if __name__ == "__main__":
    main()
