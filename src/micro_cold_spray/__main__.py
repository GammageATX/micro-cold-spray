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
    'config': "micro_cold_spray.api.config.config_app:app",
    'messaging': "micro_cold_spray.api.messaging.messaging_app:app",
    'communication': "micro_cold_spray.api.communication.communication_app:app",
    'state': "micro_cold_spray.api.state.state_app:app",
    'process': "micro_cold_spray.api.process.process_app:app",
    'data_collection': "micro_cold_spray.api.data_collection.data_collection_app:app",
    'validation': "micro_cold_spray.api.validation.validation_app:app",
    'ui': "micro_cold_spray.ui.router:app"
}

# Critical services that must start in order
STARTUP_ORDER = [
    'config',      # Must be first
    'messaging',   # Must be second
    'communication',
    'state',
    'process',
    'data_collection',
    'validation',
    'ui'
]

# Service dependencies
SERVICE_DEPENDENCIES = {
    'messaging': ['config'],
    'communication': ['config'],
    'state': ['config', 'messaging', 'communication'],
    'process': ['config', 'messaging', 'state'],
    'data_collection': ['config', 'messaging'],
    'validation': ['config', 'messaging'],
    'ui': ['config']
}

# Service processes
processes: Dict[str, mp.Process] = {}


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


def import_app(module_path: str) -> Optional[object]:
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
        return getattr(module, attr_name)
        
    except Exception as e:
        logger.error(f"Failed to import {module_path}: {e}")
        return None


def run_service(name: str, module_path: str, port: int):
    """Run service in subprocess.
    
    Args:
        name: Service name
        module_path: Module path to service
        port: Port to run on
    """
    try:
        # Import uvicorn here to avoid import before fork
        import uvicorn
        
        # Import app
        app = import_app(module_path)
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


async def start_service(name: str, port: int) -> bool:
    """Start service process.
    
    Args:
        name: Service name
        port: Port to run on
        
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
            args=(name, SERVICE_MODULES[name], port),
            name=name
        )
        process.start()
        processes[name] = process
        
        # Wait for service to be ready
        for _ in range(10):  # Wait up to 10 seconds
            if not process.is_alive():
                logger.error(f"Service {name} failed to start")
                return False
            
            # Try to connect to health endpoint
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://localhost:{port}/health", timeout=1) as resp:
                        if resp.status == 200:
                            logger.info(f"Service {name} is ready")
                            return True
            except Exception:
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
        
        # Start base port
        base_port = 8001
        port_map = {}
        
        # Start services in order
        for name in STARTUP_ORDER:
            port_map[name] = base_port
            
            # Start service
            logger.info(f"Starting {name} service...")
            if not await start_service(name, base_port):
                logger.error(f"Failed to start {name} service")
                stop_all_services()
                return
                
            # Wait for dependencies to be ready
            if name in SERVICE_DEPENDENCIES:
                for dep in SERVICE_DEPENDENCIES[name]:
                    dep_port = port_map[dep]
                    for _ in range(10):  # Wait up to 10 seconds
                        try:
                            async with aiohttp.ClientSession() as session:
                                async with session.get(f"http://localhost:{dep_port}/health", timeout=1) as resp:
                                    if resp.status == 200:
                                        break
                        except Exception:
                            await asyncio.sleep(1.0)
                    else:
                        logger.error(f"Dependency {dep} not ready for {name}")
                        stop_all_services()
                        return
            
            base_port += 1
            logger.info(f"Service {name} started successfully")
            
            # Wait briefly between services
            await asyncio.sleep(2.0)
            
        logger.info("All services started successfully")
            
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
