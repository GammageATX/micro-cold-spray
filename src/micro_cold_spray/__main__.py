# src/micro_cold_spray/__main__.py
import asyncio
import sys
from pathlib import Path
from multiprocessing import Process
import signal
import requests
from typing import Dict
import time

from loguru import logger
import uvicorn

from micro_cold_spray.ui.router import app as ui_app

BASE_DIR = Path(__file__).parent.parent.parent
LOG_DIR = BASE_DIR / "logs"


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
        level="INFO",
        enqueue=True
    )

    # Create log directory if it doesn't exist
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Add file logging with absolute path
    logger.add(
        str(LOG_DIR / "micro_cold_spray.log"),
        rotation="1 day",
        retention="30 days",
        compression="zip",
        level="INFO",
        enqueue=True
    )


def ensure_directories() -> None:
    """Create necessary directories if they don't exist."""
    dirs = [
        "logs",
        "config",
        "config/schemas",
        "data",
        "data/parameters",
        "data/patterns",
        "data/sequences",
        "data/powders",
        "data/runs"
    ]
    for dir_name in dirs:
        (BASE_DIR / dir_name).mkdir(parents=True, exist_ok=True)


async def check_service_health(port: int, retries: int = 5, delay: float = 2.0, is_critical: bool = False) -> bool:
    """Check if a service is healthy by polling its health endpoint.
    
    Args:
        port: Port number to check
        retries: Number of retry attempts
        delay: Delay between retries in seconds
        is_critical: Whether this is a critical service (increases retries and delay)
    """
    # Increase retries and delay for critical services
    if is_critical:
        retries = 10  # Double the retries for critical services
        delay = 3.0   # Increase delay for critical services
        
    url = f"http://localhost:{port}/health"
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=5)
            # Consider 404 as service starting up
            if response.status_code == 404:
                logger.warning(f"Service on port {port} starting up (health endpoint not ready)")
                if attempt < retries - 1:
                    await asyncio.sleep(delay)
                continue
                
            if response.status_code == 200:
                health_data = response.json()
                status = health_data.get("status")
                if status == "ok":
                    logger.info(f"Service on port {port} is healthy (status: {status})")
                    return True
                else:
                    logger.warning(f"Service on port {port} reported unhealthy status: {status}")
            else:
                logger.warning(f"Service on port {port} returned status code: {response.status_code}")
        except requests.ConnectionError:
            logger.warning(f"Service on port {port} not responding (attempt {attempt + 1}/{retries})")
        except Exception as e:
            logger.warning(f"Error checking service health on port {port}: {str(e)}")
        
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    
    return False


async def check_config_ready(port: int) -> bool:
    """Specifically check if config service is ready by attempting to get config.
    
    Args:
        port: Config service port number
    """
    url = f"http://localhost:{port}/config/application"
    retries = 10
    delay = 3.0
    
    for attempt in range(retries):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                config_data = response.json()
                if config_data and "config" in config_data:
                    logger.info("Config service is ready with configuration data")
                    return True
            elif response.status_code == 404:
                logger.warning(f"Config endpoint not ready (attempt {attempt + 1}/{retries})")
            else:
                logger.warning(f"Config service returned status {response.status_code}")
        except Exception as e:
            logger.warning(f"Config service not ready (attempt {attempt + 1}/{retries}): {str(e)}")
        
        if attempt < retries - 1:
            await asyncio.sleep(delay)
    
    return False


async def wait_for_service(port: int, timeout: float = 30.0) -> bool:
    """Wait for a service to start accepting connections."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            requests.get(f"http://localhost:{port}/", timeout=1)
            return True
        except requests.exceptions.RequestException:
            await asyncio.sleep(0.5)
    return False


class ServiceManager:
    """Manages service processes and their dependencies."""
    
    def __init__(self, test_mode: bool = False):
        self.processes: Dict[str, Process] = {}
        # Add test ports that are different from production
        self.test_ports = {
            'config': 8901,
            'messaging': 8907,
            'communication': 8902,
            'state': 8904,
            'process': 8903,
            'data_collection': 8905,
            'validation': 8906,
            'ui': 8900
        }
        self.prod_ports = {
            'config': 8001,
            'messaging': 8007,
            'communication': 8002,
            'state': 8004,
            'process': 8003,
            'data_collection': 8005,
            'validation': 8006,
            'ui': 8000
        }
        self.ports = self.test_ports if test_mode else self.prod_ports
        
    async def start_service(self, name: str, runner: callable, critical: bool = False, port: int = None) -> bool:
        """Start a service and verify it's running."""
        try:
            logger.info(f"Starting {name} service...")
            process = Process(target=runner)
            process.start()
            self.processes[name] = process
            
            # Skip health checks for services without ports
            if port is None and name not in self.ports:
                return True
            
            service_port = port or self.ports[name]
            
            # First wait for the service to start accepting connections
            if not await wait_for_service(service_port):
                logger.error(f"Service {name} failed to start accepting connections")
                return False
            
            # For config service, do additional readiness check
            if name == 'config':
                if not await check_config_ready(service_port):
                    logger.error("Config service failed readiness check")
                    return False
                logger.info("Config service passed readiness check")
            
            # Then check its health
            is_healthy = await check_service_health(service_port, is_critical=critical)
            
            if not is_healthy:
                if critical:
                    logger.error(f"Critical service {name} failed health check")
                    return False
                else:
                    logger.warning(f"Non-critical service {name} failed health check but continuing")
                    return True
                
            return True
            
        except Exception as e:
            logger.error(f"Error starting {name} service: {e}")
            return False

    def stop_service(self, name: str) -> None:
        """Stop a service gracefully."""
        process = self.processes.get(name)
        if process and process.is_alive():
            logger.info(f"Stopping {name} service...")
            process.terminate()
            process.join(timeout=5.0)
            if process.is_alive():
                logger.warning(f"Force killing {name} service...")
                process.kill()
                process.join()
        
        # Remove the process from the dictionary
        if name in self.processes:
            del self.processes[name]
            logger.info(f"Removed {name} service from process list")

    def stop_all(self) -> None:
        """Stop all services in reverse order."""
        for name in reversed(list(self.processes.keys())):
            self.stop_service(name)


def run_ui_process():
    """Process function to run the UI service."""
    config = uvicorn.Config(
        ui_app,
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_config_api_process():
    """Process function to run the Config API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.config.router:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_communication_api_process():
    """Process function to run the Communication API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.communication.router:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_messaging_api_process():
    """Process function to run the Messaging API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.messaging.router:app",
        host="0.0.0.0",
        port=8007,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_process_api_process():
    """Process function to run the Process API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.process.router:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_state_api_process():
    """Process function to run the State API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.state.router:app",
        host="0.0.0.0",
        port=8004,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_data_collection_api_process():
    """Process function to run the Data Collection API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.data_collection.router:app",
        host="0.0.0.0",
        port=8005,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def run_validation_api_process():
    """Process function to run the Validation API service."""
    config = uvicorn.Config(
        "micro_cold_spray.api.validation.router:app",
        host="0.0.0.0",
        port=8006,
        reload=False,
        log_level="info"
    )
    server = uvicorn.Server(config)
    asyncio.run(server.serve())


def get_test_config(service: str) -> uvicorn.Config:
    """Get test configuration for a service."""
    port_map = {
        'config': 8901,
        'messaging': 8907,
        'communication': 8902,
        'state': 8904,
        'process': 8903,
        'data_collection': 8905,
        'validation': 8906,
        'ui': 8900
    }
    
    service_map = {
        'config': "micro_cold_spray.api.config.router:app",
        'messaging': "micro_cold_spray.api.messaging.router:app",
        'communication': "micro_cold_spray.api.communication.router:app",
        'state': "micro_cold_spray.api.state.router:app",
        'process': "micro_cold_spray.api.process.router:app",
        'data_collection': "micro_cold_spray.api.data_collection.router:app",
        'validation': "micro_cold_spray.api.validation.router:app",
        'ui': "micro_cold_spray.ui.router:app"
    }
    
    return uvicorn.Config(
        service_map[service],
        host="127.0.0.1",  # Use localhost for tests
        port=port_map[service],
        reload=False,
        log_level="error"  # Reduce noise in tests
    )


async def main():
    """Application entry point with improved service management."""
    service_manager = ServiceManager()
    exit_code = 1  # Default to error exit code

    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")

        # Define service startup sequence with dependencies
        startup_sequence = [
            # UI first for fast loading
            ('ui', run_ui_process, False),
            
            # Critical services in parallel
            ('config', run_config_api_process, True),
            ('messaging', run_messaging_api_process, True),
            
            # Non-critical services
            ('communication', run_communication_api_process, False),
            ('state', run_state_api_process, False),
            ('process', run_process_api_process, False),
            ('data_collection', run_data_collection_api_process, False),
            ('validation', run_validation_api_process, False)
        ]

        # Create a map of service names to their runners
        startup_map = {name: runner for name, runner, _ in startup_sequence}

        # Start UI first
        success = await service_manager.start_service('ui', run_ui_process, False)
        if not success:
            logger.warning("UI service failed to start, but continuing...")

        # Start critical services in parallel
        critical_tasks = []
        for name in ['config', 'messaging']:
            runner = startup_map[name]
            task = asyncio.create_task(service_manager.start_service(name, runner, True))
            critical_tasks.append((name, task))

        # Wait for critical services
        for name, task in critical_tasks:
            success = await task
            if not success:
                logger.critical(f"Failed to start critical service {name}")
                raise RuntimeError(f"Critical service {name} failed to start")

        # Start non-critical services in parallel
        non_critical_tasks = []
        for name in ['communication', 'state', 'process', 'data_collection', 'validation']:
            runner = startup_map[name]
            task = asyncio.create_task(service_manager.start_service(name, runner, False))
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
                        await service_manager.start_service(name, startup_map[name], False)
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
    sys.exit(asyncio.run(main()))
