# src/micro_cold_spray/__main__.py
import os
import sys
import asyncio
import signal
import aiohttp
import multiprocessing as mp
from pathlib import Path
from typing import Dict, List, Optional
from importlib import import_module
from datetime import datetime, timedelta
from loguru import logger


# Service module paths
SERVICE_MODULES = {
    'config': "micro_cold_spray.api.config.config_app:create_config_service",
    'state': "micro_cold_spray.api.state.state_app:create_state_service",
    'communication': "micro_cold_spray.api.communication:create_communication_service",
    'process': "micro_cold_spray.api.process.process_app:create_app",
    'data_collection': "micro_cold_spray.api.data_collection.data_collection_app:DataCollectionApp",
    'validation': "micro_cold_spray.api.validation.validation_app:create_app",
    'ui': "micro_cold_spray.ui.router:create_app"
}

# Service startup order (for initial startup only)
STARTUP_ORDER = [
    'config',           # port 8001
    'state',           # port 8002
    'communication',    # port 8003
    'process',          # port 8004
    'data_collection',  # port 8005
    'validation',       # port 8006
    'ui'                # port 8000 - web interface
]

# Service processes and their state
processes: Dict[str, Dict[str, any]] = {}

# Service port mapping
PORT_MAP = {
    'config': 8001,           # Config on 8001
    'state': 8002,           # State on 8002
    'communication': 8003,    # Communication on 8003
    'process': 8004,          # Process on 8004
    'data_collection': 8005,  # Data Collection on 8005
    'validation': 8006,       # Validation on 8006
    'ui': 8000               # UI on 8000 - web interface
}

# Service recovery settings
MAX_RESTART_ATTEMPTS = 3   # Maximum number of restart attempts
RESTART_COOLDOWN = 60      # Seconds to wait between restart attempts
HEALTH_CHECK_INTERVAL = 5  # Seconds between health checks


def ensure_directories():
    """Ensure required directories exist."""
    required_dirs = [
        Path("logs"),
        Path("config"),
        Path("config/schemas")
    ]
    
    for dir_path in required_dirs:
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Ensured directory exists: {dir_path}")


def import_app(module_path: str, test_mode: bool = False) -> Optional[object]:
    """Import application from module path.
    
    Args:
        module_path: Module path in format 'module:attribute'
        test_mode: Whether to run in test mode
        
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
            app_instance = app()
            
            # Initialize service state for factory-created apps
            if hasattr(app_instance, 'state'):
                service_name = module_name.split('.')[-2]
                if service_name == 'validation':
                    from micro_cold_spray.api.validation.validation_service import ValidationService
                    app_instance.state.validation_service = ValidationService()
                elif service_name == 'process':
                    from micro_cold_spray.api.process.process_service import ProcessService
                    app_instance.state.process_service = ProcessService()
                elif service_name == 'communication':
                    # Communication service needs config from app
                    from micro_cold_spray.api.communication.communication_service import CommunicationService
                    if hasattr(app_instance, 'config'):
                        app_instance.state.communication_service = CommunicationService(app_instance.config)
                    else:
                        logger.error("Communication app missing config")
                        return None
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
            
            return app_instance
            
        elif attr_name in ["DataCollectionApp"]:
            # Apps that handle their own FastAPI params and state
            return app()
        elif isinstance(app, type):
            # Class that needs to be instantiated with FastAPI args
            return app(
                title=module_name.split('.')[-2].replace('_', ' ').title(),
                description=f"Service for {module_name.split('.')[-2].replace('_', ' ')}",
                version="1.0.0"
            )
        else:
            # Direct app instance
            return app
        
    except Exception as e:
        logger.error(f"Failed to import {module_path}: {e}")
        return None


def run_service(name: str, module_path: str, port: int, test_mode: bool = False):
    """Run service in subprocess.
    
    Args:
        name: Service name
        module_path: Module path to service
        port: Port to run on
        test_mode: Whether to run in test mode
    """
    try:
        # Import uvicorn here to avoid import before fork
        import uvicorn
        
        # Set test mode environment variable
        if test_mode:
            os.environ["TEST_MODE"] = "true"
        
        # Import app
        app = import_app(module_path, test_mode)
        if not app:
            logger.error(f"Failed to import app for {name}")
            return
            
        # Run service
        logger.info(f"Starting {name} service on port {port}")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"Error running {name} service: {e}")


async def check_service_health(name: str, port: int) -> bool:
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
    except Exception:
        return False


async def start_service(name: str, port: int, test_mode: bool = False) -> bool:
    """Start service process.
    
    Args:
        name: Service name
        port: Port to run on
        test_mode: Whether to run in test mode
        
    Returns:
        True if service started successfully
    """
    try:
        if name not in SERVICE_MODULES:
            logger.error(f"Unknown service: {name}")
            return False
            
        # Create and start process
        process = mp.Process(
            target=run_service,
            args=(name, SERVICE_MODULES[name], port, test_mode),
            name=name
        )
        process.start()
        
        # Initialize process state
        processes[name] = {
            'process': process,
            'port': port,
            'restart_count': 0,
            'last_restart': datetime.now(),
            'last_health_check': datetime.now(),
            'healthy': False
        }
        
        # Wait for service to be ready
        for _ in range(20):  # Wait up to 20 seconds
            if not process.is_alive():
                logger.error(f"Service {name} failed to start")
                return False
            
            if await check_service_health(name, port):
                processes[name]['healthy'] = True
                logger.info(f"Service {name} is ready")
                return True
                
            await asyncio.sleep(1.0)
            
        logger.error(f"Service {name} failed to become ready")
        return False
        
    except Exception as e:
        logger.error(f"Error starting {name} service: {e}")
        return False


async def monitor_and_recover_services():
    """Monitor service health and attempt recovery if needed."""
    while True:
        try:
            current_time = datetime.now()
            
            for name, info in list(processes.items()):
                # Skip if too soon for next health check
                if (current_time - info['last_health_check']) < timedelta(seconds=HEALTH_CHECK_INTERVAL):
                    continue
                
                # Update last health check time
                info['last_health_check'] = current_time
                
                # Check process health
                process_alive = info['process'].is_alive()
                service_healthy = await check_service_health(name, info['port'])
                
                if not process_alive or not service_healthy:
                    logger.warning(f"Service {name} is unhealthy (alive={process_alive}, healthy={service_healthy})")
                    
                    # Check if we can attempt restart
                    if info['restart_count'] >= MAX_RESTART_ATTEMPTS:
                        if (current_time - info['last_restart']) > timedelta(seconds=RESTART_COOLDOWN):
                            # Reset restart count after cooldown
                            info['restart_count'] = 0
                        else:
                            logger.error(f"Service {name} has failed too many times, waiting for cooldown")
                            continue
                    
                    # Attempt restart
                    logger.info(f"Attempting to restart {name} service (attempt {info['restart_count'] + 1})")
                    
                    # Stop old process if it's still running
                    if process_alive:
                        info['process'].terminate()
                        info['process'].join(timeout=5.0)
                        if info['process'].is_alive():
                            info['process'].kill()
                            info['process'].join()
                    
                    # Start new process
                    if await start_service(name, info['port'], False):
                        logger.info(f"Successfully restarted {name} service")
                    else:
                        info['restart_count'] += 1
                        info['last_restart'] = current_time
                        logger.error(f"Failed to restart {name} service")
                else:
                    info['healthy'] = True
                    
        except Exception as e:
            logger.error(f"Error in service monitor: {e}")
            
        await asyncio.sleep(1.0)


def stop_service(name: str):
    """Stop service process.
    
    Args:
        name: Service name
    """
    if name in processes:
        info = processes[name]
        process = info['process']
        if process.is_alive():
            process.terminate()
            process.join(timeout=5.0)
            if process.is_alive():
                process.kill()
                process.join()
        del processes[name]
        logger.info(f"Stopped {name} service")


def stop_all_services():
    """Stop all service processes."""
    # Stop in reverse order
    for name in reversed(STARTUP_ORDER):
        stop_service(name)


def signal_handler(signum, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {signum}")
    stop_all_services()
    sys.exit(0)


async def main(test_mode: bool = False):
    """Main entry point.
    
    Args:
        test_mode: Whether to run in test mode
    """
    try:
        # Ensure directories exist
        ensure_directories()
        
        # Register signal handlers
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start services in order (initial startup)
        for name in STARTUP_ORDER:
            logger.info(f"Starting {name} service...")
            if not await start_service(name, PORT_MAP[name], test_mode):
                logger.error(f"Failed to start {name} service")
                stop_all_services()
                return
            
            logger.info(f"Service {name} started successfully on port {PORT_MAP[name]}")
            await asyncio.sleep(2.0)
            
        logger.info("All services started successfully")
        if test_mode:
            logger.info("Running in TEST MODE - using mock tags and configurations")
            
        # Start service monitor
        monitor_task = asyncio.create_task(monitor_and_recover_services())
        
        try:
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            monitor_task.cancel()
            try:
                await monitor_task
            except asyncio.CancelledError:
                pass
                    
    except Exception as e:
        logger.error(f"Application error: {e}")
        
    finally:
        stop_all_services()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    # Get test mode from environment
    TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
    sys.exit(asyncio.run(main(test_mode=TEST_MODE)))
