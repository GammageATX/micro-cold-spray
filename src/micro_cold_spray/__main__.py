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
from loguru import logger


# Service module paths
SERVICE_MODULES = {
    'config': "micro_cold_spray.api.config.config_app:create_config_service",
    'messaging': "micro_cold_spray.api.messaging.messaging_app:MessagingApp",
    'communication': "micro_cold_spray.api.communication.communication_app:create_app",
    'state': "micro_cold_spray.api.state.state_app:create_state_service",
    'data_collection': "micro_cold_spray.api.data_collection.data_collection_app:DataCollectionApp",
    'validation': "micro_cold_spray.api.validation.validation_app:create_app",
    'ui': "micro_cold_spray.api.ui.router:app"
}

# Critical services that must start in order
STARTUP_ORDER = [
    'config',           # Must be first - port 8001
    'messaging',        # Must be second - port 8002
    'communication',    # port 8003
    'state',            # port 8004
    'data_collection',  # port 8006
    'validation',       # port 8007
    'ui'                # port 8000 - web interface
]

# Service dependencies
SERVICE_DEPENDENCIES = {
    'messaging': ['config'],
    'communication': ['config', 'messaging'],
    'state': ['config', 'messaging', 'communication'],
    'data_collection': ['config', 'messaging', 'communication'],
    'validation': ['config', 'messaging', 'communication'],
    'ui': ['config', 'messaging']
}

# Service processes
processes: Dict[str, mp.Process] = {}


def ensure_directories():
    """Ensure required directories exist."""
    required_dirs = [
        Path("logs"),
        Path("config"),
        Path("config/schemas"),
        Path("config/validation_rules")  # Added for validation rules
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
            return app()
        elif attr_name in ["DataCollectionApp", "StateApp", "MessagingApp"]:
            # Apps that handle their own FastAPI params
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
            
        if name in processes:
            logger.warning(f"Service {name} is already running")
            return True
            
        # Check dependencies
        if name in SERVICE_DEPENDENCIES:
            for dep in SERVICE_DEPENDENCIES[name]:
                if dep not in processes or not processes[dep].is_alive():
                    logger.error(f"Service {name} requires {dep} to be running")
                    return False
                    
        # Create and start process
        process = mp.Process(
            target=run_service,
            args=(name, SERVICE_MODULES[name], port, test_mode),
            name=name
        )
        process.start()
        processes[name] = process
        
        # Wait for service to be ready
        for _ in range(20):  # Increased retries to 20 seconds
            if not process.is_alive():
                logger.error(f"Service {name} failed to start")
                return False
            
            # Try to connect to health endpoint
            try:
                async with aiohttp.ClientSession() as session:
                    # Each service has its own health endpoint pattern
                    endpoint = {
                        'messaging': '/messaging/health',
                        'config': '/health',
                        'communication': '/health',
                        'state': '/health',
                        'data_collection': '/health',
                        'validation': '/health',
                        'ui': '/health'
                    }.get(name, '/health')
                    
                    async with session.get(f"http://localhost:{port}{endpoint}", timeout=2) as resp:
                        if resp.status == 200:
                            # Wait a bit longer after health check passes
                            await asyncio.sleep(2.0)
                            logger.info(f"Service {name} is ready")
                            return True
            except Exception as e:
                logger.debug(f"Health check attempt failed for {name}: {e}")
                pass
                
            await asyncio.sleep(1.0)
            
        logger.error(f"Service {name} failed to become ready")
        return False
        
    except Exception as e:
        logger.error(f"Error starting {name} service: {e}")
        return False


def stop_service(name: str):
    """Stop service process.
    
    Args:
        name: Service name
    """
    if name in processes:
        process = processes[name]
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
        
        # Map services to ports
        port_map = {
            'config': 8001,           # Config on 8001
            'messaging': 8002,        # Messaging on 8002
            'communication': 8003,    # Communication on 8003
            'state': 8004,           # State on 8004
            'data_collection': 8005,  # Data Collection on 8005
            'validation': 8007,       # Validation on 8007
            'ui': 8000               # UI on 8000 - web interface
        }
        
        # Start services in order
        for name in STARTUP_ORDER:
            # Wait for dependencies to be ready first
            if name in SERVICE_DEPENDENCIES:
                for dep in SERVICE_DEPENDENCIES[name]:
                    dep_port = port_map[dep]
                    logger.info(f"Waiting for dependency {dep} on port {dep_port}...")
                    
                    for _ in range(30):  # Wait up to 30 seconds
                        try:
                            async with aiohttp.ClientSession() as session:
                                endpoint = '/messaging/health' if dep == 'messaging' else '/health'
                                async with session.get(f"http://localhost:{dep_port}{endpoint}", timeout=1) as resp:
                                    if resp.status == 200:
                                        logger.info(f"Dependency {dep} is ready")
                                        break
                        except Exception:
                            await asyncio.sleep(1.0)
                    else:
                        logger.error(f"Dependency {dep} not ready for {name}")
                        stop_all_services()
                        return
            
            # Start service
            logger.info(f"Starting {name} service...")
            if not await start_service(name, port_map[name], test_mode):
                logger.error(f"Failed to start {name} service")
                stop_all_services()
                return
            
            logger.info(f"Service {name} started successfully on port {port_map[name]}")
            
            # Wait briefly between services
            await asyncio.sleep(2.0)
            
        logger.info("All services started successfully")
        if test_mode:
            logger.info("Running in TEST MODE - using mock tags and configurations")
            
        # Keep running until interrupted
        while True:
            await asyncio.sleep(1.0)
            
            # Check if any process died
            for name, process in list(processes.items()):
                if not process.is_alive():
                    logger.error(f"Service {name} died unexpectedly")
                    stop_all_services()
                    return
                    
    except Exception as e:
        logger.error(f"Application error: {e}")
        
    finally:
        stop_all_services()
        logger.info("Application shutdown complete")


if __name__ == "__main__":
    # Get test mode from environment
    TEST_MODE = os.getenv("TEST_MODE", "").lower() in ("true", "1", "yes")
    sys.exit(asyncio.run(main(test_mode=TEST_MODE)))
