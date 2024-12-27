"""MicroColdSpray System Main Application.

This module serves as the entry point for the MicroColdSpray system.
It handles service orchestration, health monitoring, and system lifecycle.
"""

import os
import sys
import asyncio
import signal
import aiohttp
import uvicorn
import multiprocessing as mp
from pathlib import Path
from typing import Dict, Optional, Any
from importlib import import_module
from datetime import datetime, timedelta
from loguru import logger

from micro_cold_spray import __version__


class ServiceConfig:
    """Service configuration constants."""
    
    # Service module paths
    MODULES = {
        'config': "micro_cold_spray.api.config.config_app:create_config_service",
        'state': "micro_cold_spray.api.state.state_app:create_state_service",
        'communication': "micro_cold_spray.api.communication.communication_app:create_communication_service",
        'process': "micro_cold_spray.api.process.process_app:create_app",
        'data_collection': "micro_cold_spray.api.data_collection.data_collection_app:create_data_collection_app",
        'validation': "micro_cold_spray.api.validation.validation_app:create_app",
        'ui': "micro_cold_spray.ui.router:create_app"
    }

    # Service startup order with dependencies
    STARTUP_ORDER = [
        'config',            # Configuration service (port 8001)
        'state',            # State management service (port 8002)
        'communication',     # Hardware communication service (port 8003)
        'process',          # Process control service (port 8004)
        'data_collection',  # Data collection service (port 8005)
        'validation',       # Validation service (port 8006)
        'ui'               # Web interface (port 8000)
    ]

    # Service port mapping
    PORTS = {
        'config': 8001,
        'state': 8002,
        'communication': 8003,
        'process': 8004,
        'data_collection': 8005,
        'validation': 8006,
        'ui': 8000
    }

    # Recovery settings
    MAX_RESTART_ATTEMPTS = 3    # Maximum number of restart attempts
    RESTART_COOLDOWN = 60       # Seconds to wait between restart attempts
    HEALTH_CHECK_INTERVAL = 5   # Seconds between health checks
    STARTUP_TIMEOUT = 20        # Seconds to wait for service startup
    SHUTDOWN_TIMEOUT = 10       # Seconds to wait for service shutdown

    # Service dependencies
    DEPENDENCIES = {
        'communication': ['config', 'state'],
        'process': ['config', 'state', 'communication'],
        'data_collection': ['config', 'state', 'communication'],
        'validation': ['config'],
        'ui': []
    }


class ServiceManager:
    """Service orchestration and management."""

    def __init__(self, test_mode: bool = False):
        """Initialize service manager.
        
        Args:
            test_mode: Whether to run in test mode
        """
        self.test_mode = test_mode
        self.processes: Dict[str, Dict[str, Any]] = {}
        self.running = True
        self._setup_logging()
        self._setup_signal_handlers()

    def _setup_logging(self) -> None:
        """Configure logging for the application."""
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        # Remove default handler
        logger.remove()
        
        # Add console handler with colored output and structured format
        log_format = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(sys.stderr, format=log_format, level="INFO")
        
        # Add file handler with rotation and compression
        logger.add(
            log_dir / "micro_cold_spray_{time}.log",
            rotation="1 day",
            retention="30 days",
            compression="zip",
            level="DEBUG"
        )

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, self._handle_shutdown)

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals.
        
        Args:
            signum: Signal number
            frame: Current stack frame
        """
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False

    async def ensure_directories(self) -> None:
        """Ensure required directories exist."""
        required_dirs = [
            Path("logs"),
            Path("config"),
            Path("config/schemas"),
            Path("data")  # For data collection service
        ]
        
        for dir_path in required_dirs:
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Ensured directory exists: {dir_path}")

    def import_app(self, module_path: str) -> Optional[object]:
        """Import application from module path.
        
        Args:
            module_path: Module path in format 'module:attribute'
            
        Returns:
            Imported application or None if import fails
        """
        try:
            if ":" not in module_path:
                logger.error(f"Invalid module path format: {module_path}")
                return None
                
            module_name, attr_name = module_path.split(":")
            module = import_module(module_name)
            app = getattr(module, attr_name)
            
            # Handle different app types
            if attr_name.startswith('create_'):
                # Factory function
                app_instance = app(test_mode=self.test_mode)
                
                # Initialize service state for factory-created apps
                if hasattr(app_instance, 'state'):
                    service_name = module_name.split('.')[-2]
                    self._initialize_service_state(app_instance, service_name)
                
                return app_instance
                
            elif isinstance(app, type):
                # Class that needs to be instantiated with FastAPI args
                return app(
                    title=module_name.split('.')[-2].replace('_', ' ').title(),
                    description=f"Service for {module_name.split('.')[-2].replace('_', ' ')}",
                    version=__version__
                )
            else:
                # Direct app instance
                return app
            
        except Exception as e:
            logger.error(f"Failed to import {module_path}: {e}")
            return None

    def _initialize_service_state(self, app_instance: Any, service_name: str) -> None:
        """Initialize service state based on service type.
        
        Args:
            app_instance: Application instance
            service_name: Name of the service
        """
        try:
            if service_name == 'validation':
                from micro_cold_spray.api.validation.validation_service import ValidationService
                app_instance.state.validation_service = ValidationService()
            elif service_name == 'process':
                from micro_cold_spray.api.process.process_service import ProcessService
                app_instance.state.process_service = ProcessService()
            elif service_name == 'communication':
                from micro_cold_spray.api.communication.communication_service import CommunicationService
                if hasattr(app_instance, 'config'):
                    app_instance.state.communication_service = CommunicationService(app_instance.config)
                else:
                    logger.error("Communication app missing config")
            elif service_name == 'config':
                from micro_cold_spray.api.config.services.file_service import FileService
                from micro_cold_spray.api.config.services.format_service import FormatService
                from micro_cold_spray.api.config.services.schema_service import SchemaService
                app_instance.state.file = FileService()
                app_instance.state.format = FormatService()
                app_instance.state.schema = SchemaService()
            elif service_name == 'state':
                from micro_cold_spray.api.state.state_service import StateService
                app_instance.state.service = StateService()
            elif service_name == 'data_collection':
                from micro_cold_spray.api.data_collection.data_collection_service import DataCollectionService
                app_instance.state.service = DataCollectionService()
        except Exception as e:
            logger.error(f"Failed to initialize state for {service_name}: {e}")

    async def check_service_health(self, name: str, port: int) -> bool:
        """Check if a service is healthy.
        
        Args:
            name: Service name
            port: Service port
            
        Returns:
            bool: True if service is healthy
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://localhost:{port}/health", timeout=2) as resp:
                    return resp.status == 200
        except Exception as e:
            logger.debug(f"Health check failed for {name}: {e}")
            return False

    async def check_dependencies(self, service_name: str) -> bool:
        """Check if service dependencies are healthy.
        
        Args:
            service_name: Name of service to check dependencies for
            
        Returns:
            bool: True if all dependencies are healthy
        """
        dependencies = ServiceConfig.DEPENDENCIES.get(service_name, [])
        for dep in dependencies:
            if dep not in self.processes:
                logger.error(f"Dependency {dep} not found for {service_name}")
                return False
            if not self.processes[dep]['healthy']:
                logger.error(f"Dependency {dep} not healthy for {service_name}")
                return False
        return True

    async def start_service(self, name: str, port: int) -> bool:
        """Start service process.
        
        Args:
            name: Service name
            port: Port to run on
            
        Returns:
            True if service started successfully
        """
        try:
            if name not in ServiceConfig.MODULES:
                logger.error(f"Unknown service: {name}")
                return False

            # Check dependencies
            if not await self.check_dependencies(name):
                logger.error(f"Dependencies not met for {name}")
                return False
                
            # Create and start process using factory function path
            process = mp.Process(
                target=uvicorn.run,
                args=(ServiceConfig.MODULES[name],),
                kwargs={
                    "host": "0.0.0.0",
                    "port": port,
                    "factory": True,
                    "log_level": "info",
                    "lifespan": "on",
                    "timeout_keep_alive": 60
                },
                name=name
            )
            process.start()
            
            # Initialize process state
            self.processes[name] = {
                'process': process,
                'port': port,
                'restart_count': 0,
                'last_restart': datetime.now(),
                'last_health_check': datetime.now(),
                'healthy': False
            }
            
            # Wait for service to be ready
            for _ in range(ServiceConfig.STARTUP_TIMEOUT):
                if not process.is_alive():
                    logger.error(f"Service {name} failed to start")
                    return False
                
                if await self.check_service_health(name, port):
                    self.processes[name]['healthy'] = True
                    logger.info(f"Service {name} is ready")
                    return True
                    
                await asyncio.sleep(1.0)
                
            logger.error(f"Service {name} failed to become ready")
            return False
            
        except Exception as e:
            logger.error(f"Error starting {name} service: {e}")
            return False

    async def monitor_and_recover_services(self) -> None:
        """Monitor service health and attempt recovery if needed."""
        while self.running:
            try:
                current_time = datetime.now()
                
                for name, info in list(self.processes.items()):
                    # Skip if too soon for next health check
                    if (current_time - info['last_health_check']) < timedelta(seconds=ServiceConfig.HEALTH_CHECK_INTERVAL):
                        continue
                    
                    # Update last health check time
                    info['last_health_check'] = current_time
                    
                    # Check process health
                    process_alive = info['process'].is_alive()
                    service_healthy = await self.check_service_health(name, info['port'])
                    
                    if not process_alive or not service_healthy:
                        await self._handle_service_failure(name, info)
                    else:
                        # Reset restart count on successful health check
                        info['restart_count'] = 0
                        info['healthy'] = True
                
                await asyncio.sleep(1.0)
                
            except Exception as e:
                logger.error(f"Error in service monitoring: {e}")
                await asyncio.sleep(5.0)

    async def _handle_service_failure(self, name: str, info: Dict[str, Any]) -> None:
        """Handle service failure and attempt recovery.
        
        Args:
            name: Service name
            info: Service process information
        """
        logger.warning(f"Service {name} is unhealthy")
        
        # Check if we can restart
        if info['restart_count'] >= ServiceConfig.MAX_RESTART_ATTEMPTS:
            if (datetime.now() - info['last_restart']) > timedelta(seconds=ServiceConfig.RESTART_COOLDOWN):
                # Reset counter after cooldown
                info['restart_count'] = 0
            else:
                logger.error(f"Service {name} exceeded restart attempts")
                return
        
        # Attempt restart
        logger.info(f"Attempting to restart {name}")
        info['process'].terminate()
        try:
            info['process'].join(timeout=5.0)
        except TimeoutError:
            info['process'].kill()
        
        info['restart_count'] += 1
        info['last_restart'] = datetime.now()
        
        # Start new process
        await self.start_service(name, info['port'])

    async def shutdown_services(self) -> None:
        """Gracefully shutdown all services."""
        logger.info("Shutting down services...")
        
        # Shutdown in reverse order
        for name in reversed(ServiceConfig.STARTUP_ORDER):
            if name in self.processes:
                try:
                    logger.info(f"Stopping {name} service...")
                    info = self.processes[name]
                    info['process'].terminate()
                    info['process'].join(timeout=ServiceConfig.SHUTDOWN_TIMEOUT)
                    if info['process'].is_alive():
                        logger.warning(f"Force killing {name} service")
                        info['process'].kill()
                except Exception as e:
                    logger.error(f"Error stopping {name} service: {e}")

    async def run(self) -> None:
        """Run the service manager."""
        try:
            logger.info(f"Starting MicroColdSpray System v{__version__}")
            if self.test_mode:
                logger.info("Running in TEST MODE")
            
            await self.ensure_directories()
            
            # Start services in order
            for service_name in ServiceConfig.STARTUP_ORDER:
                port = ServiceConfig.PORTS[service_name]
                logger.info(f"Starting {service_name} service on port {port}")
                if not await self.start_service(service_name, port):
                    logger.error(f"Failed to start {service_name} service")
                    await self.shutdown_services()
                    return
            
            # Monitor services
            await self.monitor_and_recover_services()
            
        except Exception as e:
            logger.error(f"System error: {e}")
        finally:
            await self.shutdown_services()


def main() -> None:
    """Main entry point."""
    # Get test mode from environment
    test_mode = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
    
    if sys.platform == 'win32':
        # Windows specific setup for multiprocessing
        mp.freeze_support()
        mp.set_start_method('spawn')
    else:
        # Unix specific setup
        mp.set_start_method('fork')
    
    # Create and run service manager
    manager = ServiceManager(test_mode=test_mode)
    asyncio.run(manager.run())


if __name__ == "__main__":
    main()
