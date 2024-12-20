# src/micro_cold_spray/__main__.py
import asyncio
import sys
from pathlib import Path
from multiprocessing import Process
import signal
import aiohttp
from typing import Dict, Optional
import time
import os

from loguru import logger
import uvicorn

from micro_cold_spray.ui.router import app as ui_app

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / "logs"
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"

# Service definitions
SERVICE_PORTS = {
    'config': (8901, 8001),  # (test_port, prod_port)
    'messaging': (8907, 8007),
    'communication': (8902, 8002),
    'state': (8904, 8004),
    'process': (8903, 8003),
    'data_collection': (8905, 8005),
    'validation': (8906, 8006),
    'ui': (8900, 8000)
}

SERVICE_MODULES = {
    'config': "micro_cold_spray.api.config.config_app:create_app",
    'messaging': "micro_cold_spray.api.messaging.messaging_app:create_app",
    'communication': "micro_cold_spray.api.communication.communication_app:create_app",
    'state': "micro_cold_spray.api.state.state_app:create_app",
    'process': "micro_cold_spray.api.process.process_app:create_app",
    'data_collection': "micro_cold_spray.api.data_collection.data_collection_app:create_app",
    'validation': "micro_cold_spray.api.validation.validation_app:create_app",
    'ui': "micro_cold_spray.ui.router:app"
}


def setup_logging() -> None:
    """Configure loguru for application logging."""
    logger.remove()  # Remove default handler

    # Break up log format into smaller parts
    time_fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green>"
    level_fmt = "<level>{level: <8}</level>"
    location_fmt = "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>"
    message_fmt = "<level>{message}</level>"

    log_format = f"{time_fmt} | {level_fmt} | {location_fmt} - {message_fmt}"

    # Add console logging
    logger.add(
        sys.stderr,
        format=log_format,
        level="INFO",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )

    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Add file logging with rotation
    logger.add(
        str(LOG_DIR / "micro_cold_spray.log"),
        rotation="1 day",
        retention="30 days",
        compression="zip",
        level="INFO",
        enqueue=True,
        backtrace=True,
        diagnose=True
    )


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    dirs = [
        LOG_DIR,
        CONFIG_DIR,
        CONFIG_DIR / "schemas",
        DATA_DIR,
        DATA_DIR / "parameters",
        DATA_DIR / "patterns",
        DATA_DIR / "sequences",
        DATA_DIR / "powders",
        DATA_DIR / "runs"
    ]
    for dir_path in dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


async def check_service_health(port: int, retries: int = 5, delay: float = 2.0, is_critical: bool = False) -> bool:
    """Check if a service is healthy by polling its health endpoint."""
    if is_critical:
        retries = 10
        delay = 3.0
        
    url = f"http://localhost:{port}/health"
    async with aiohttp.ClientSession() as session:
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 404:
                        logger.warning(f"Service on port {port} starting up (health endpoint not ready)")
                        if attempt < retries - 1:
                            await asyncio.sleep(delay)
                        continue
                        
                    if response.status == 200:
                        data = await response.json()
                        status = data.get("status")
                        if status == "ok":
                            logger.info(f"Service on port {port} is healthy")
                            return True
                        logger.warning(f"Service on port {port} reported unhealthy status: {status}")
                    else:
                        logger.warning(f"Service on port {port} returned status code: {response.status}")
            except aiohttp.ClientError:
                logger.warning(f"Service on port {port} not responding (attempt {attempt + 1}/{retries})")
            except Exception as e:
                logger.warning(f"Error checking service health on port {port}: {str(e)}")
            
            if attempt < retries - 1:
                await asyncio.sleep(delay)
        
        return False


async def check_config_ready(port: int) -> bool:
    """Check if config service is ready by attempting to get config."""
    url = f"http://localhost:{port}/config/application"
    retries = 10
    delay = 3.0
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(retries):
            try:
                async with session.get(url, timeout=5) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data and "config" in data:
                            logger.info("Config service is ready")
                            return True
                    elif response.status == 404:
                        logger.warning(f"Config endpoint not ready (attempt {attempt + 1}/{retries})")
                    else:
                        logger.warning(f"Config service returned status {response.status}")
            except Exception as e:
                logger.warning(f"Config service not ready (attempt {attempt + 1}/{retries}): {str(e)}")
            
            if attempt < retries - 1:
                await asyncio.sleep(delay)
        
        return False


async def wait_for_service(port: int, timeout: float = 30.0) -> bool:
    """Wait for a service to start accepting connections."""
    start_time = time.time()
    async with aiohttp.ClientSession() as session:
        while time.time() - start_time < timeout:
            try:
                async with session.get(f"http://localhost:{port}/", timeout=1):
                    return True
            except aiohttp.ClientError:
                await asyncio.sleep(0.5)
        return False


def run_service(service_name: str, test_mode: bool = False) -> None:
    """Run a service using uvicorn.
    
    Args:
        service_name: Name of service to run
        test_mode: Whether to run in test mode
    """
    try:
        port = SERVICE_PORTS[service_name][0 if test_mode else 1]
        module_path = SERVICE_MODULES[service_name]
        
        # Split module path into module and attribute
        module_str, attr = module_path.split(":")
        
        config = uvicorn.Config(
            module_str,
            factory=True if attr == "create_app" else False,
            host="127.0.0.1" if test_mode else "0.0.0.0",
            port=port,
            reload=False,
            log_level="error" if test_mode else "info",
            workers=1
        )
        server = uvicorn.Server(config)
        asyncio.run(server.serve())
    except Exception as e:
        logger.error(f"Error running service {service_name}: {e}")
        sys.exit(1)


class ServiceManager:
    """Manages service processes and their dependencies."""
    
    def __init__(self, test_mode: bool = False):
        """Initialize service manager.
        
        Args:
            test_mode: Whether to use test ports
        """
        self.processes: Dict[str, Process] = {}
        self.test_mode = test_mode
        self.ports = {name: ports[0 if test_mode else 1]
                      for name, ports in SERVICE_PORTS.items()}
        
    async def start_service(self, name: str, critical: bool = False) -> bool:
        """Start a service and verify it's running.
        
        Args:
            name: Service name
            critical: Whether this is a critical service
            
        Returns:
            bool: True if service started successfully, False otherwise
        """
        try:
            logger.info(f"Starting {name} service...")
            process = Process(
                target=run_service,
                args=(name, self.test_mode),
                name=f"Service-{name}"
            )
            process.start()
            self.processes[name] = process
            
            # Get port for health check
            port = self.ports.get(name)
            if not port:
                logger.warning(f"No port configured for service {name}")
                return True  # Assume success for services without ports
            
            # Wait for service to start accepting connections
            if not await wait_for_service(port):
                logger.error(f"Service {name} failed to start accepting connections")
                return False
            
            # For config service, do additional readiness check
            if name == 'config':
                if not await check_config_ready(port):
                    logger.error("Config service failed readiness check")
                    return False
                logger.info("Config service passed readiness check")
            
            # Check service health
            is_healthy = await check_service_health(port, is_critical=critical)
            if not is_healthy and critical:
                logger.error(f"Critical service {name} failed health check")
                return False
            elif not is_healthy:
                logger.warning(f"Non-critical service {name} failed health check but continuing")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting {name} service: {e}")
            return False

    def stop_service(self, name: str) -> None:
        """Stop a service gracefully.
        
        Args:
            name: Service name to stop
        """
        process = self.processes.get(name)
        if process and process.is_alive():
            logger.info(f"Stopping {name} service...")
            process.terminate()
            process.join(timeout=5.0)
            if process.is_alive():
                logger.warning(f"Force killing {name} service...")
                process.kill()
                process.join()
        
        if name in self.processes:
            del self.processes[name]
            logger.info(f"Removed {name} service from process list")

    def stop_all(self) -> None:
        """Stop all services in reverse order."""
        for name in reversed(list(self.processes.keys())):
            self.stop_service(name)


async def main(test_mode: bool = False) -> int:
    """Application entry point.
    
    Args:
        test_mode: Whether to run in test mode
        
    Returns:
        int: Exit code (0 for success, 1 for error)
    """
    service_manager = ServiceManager(test_mode=test_mode)
    exit_code = 1  # Default to error exit code

    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")

        # Define service startup sequence
        startup_sequence = [
            ('ui', False),
            ('config', True),
            ('messaging', True),
            ('communication', False),
            ('state', False),
            ('process', False),
            ('data_collection', False),
            ('validation', False)
        ]

        # Start UI first
        success = await service_manager.start_service('ui', False)
        if not success:
            logger.warning("UI service failed to start, but continuing...")

        # Start critical services in parallel
        critical_tasks = []
        for name, is_critical in startup_sequence[1:3]:  # config and messaging
            task = asyncio.create_task(service_manager.start_service(name, True))
            critical_tasks.append((name, task))

        # Wait for critical services
        for name, task in critical_tasks:
            success = await task
            if not success:
                logger.critical(f"Failed to start critical service {name}")
                raise RuntimeError(f"Critical service {name} failed to start")

        # Start non-critical services in parallel
        non_critical_tasks = []
        for name, is_critical in startup_sequence[3:]:
            task = asyncio.create_task(service_manager.start_service(name, False))
            non_critical_tasks.append((name, task))

        def shutdown_handler(sig, frame):
            logger.info("Shutdown requested...")
            service_manager.stop_all()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Monitor services
        while True:
            for name, process in service_manager.processes.items():
                if not process.is_alive():
                    if name in ['config', 'messaging', 'communication']:
                        logger.critical(f"Critical service {name} died - shutting down system")
                        service_manager.stop_all()
                        return 1
                    else:
                        logger.warning(f"Non-critical service {name} died - attempting restart")
                        await service_manager.start_service(name, False)
            await asyncio.sleep(5)

    except KeyboardInterrupt:
        logger.info("Shutdown requested by user...")
        exit_code = 0
    except Exception as e:
        logger.exception(f"Critical application error: {e}")
    finally:
        service_manager.stop_all()
        logger.info("Application shutdown complete")
        return exit_code


if __name__ == "__main__":
    # Get test mode from environment
    TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
    sys.exit(asyncio.run(main(test_mode=TEST_MODE)))
