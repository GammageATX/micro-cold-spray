# src/micro_cold_spray/__main__.py
import asyncio
import sys
from datetime import datetime
from pathlib import Path
from multiprocessing import Process
import signal

from loguru import logger
import uvicorn

from micro_cold_spray.ui.router import app as ui_app


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
    """Create necessary directories if they don't exist."""
    dirs = [
        "logs",
        "config",
        "config/schemas",
        "data"
    ]
    for dir_name in dirs:
        Path(dir_name).mkdir(exist_ok=True)


def run_ui_process():
    """Process function to run the UI service."""
    async def run_ui():
        config = uvicorn.Config(ui_app, host="0.0.0.0", port=8000, reload=True)
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(run_ui())


def run_config_api_process():
    """Process function to run the Config API service."""
    async def run_config_api():
        config = uvicorn.Config(
            "micro_cold_spray.api.config.router:app",
            host="0.0.0.0",
            port=8001,
            reload=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(run_config_api())


def run_communication_api_process():
    """Process function to run the Communication API service."""
    async def run_communication_api():
        config = uvicorn.Config(
            "micro_cold_spray.api.communication.router:app",
            host="0.0.0.0",
            port=8002,
            reload=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    asyncio.run(run_communication_api())


def run_messaging_api_process():
    """Process function to run the Messaging API service."""
    uvicorn.run(
        "micro_cold_spray.api.messaging.router:app",
        host="0.0.0.0",
        port=8007,
        reload=True,
        log_level="info"
    )


# Define critical and non-critical services
CRITICAL_SERVICES = {
    'config',          # Configuration must be available
    'messaging',       # Required for inter-service communication
    'communication'    # Required for hardware interface
}

NON_CRITICAL_SERVICES = {
    'state',            # State tracking can recover
    'process',          # Process control can be restarted
    'data_collection',  # Data collection can be interrupted
    'validation',       # Validation can be restarted
    'ui'                # UI can be refreshed
}


async def main():
    """Application entry point."""
    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")

        # Dictionary to track all processes
        processes = {}

        # Start critical services first
        logger.info("Starting critical services...")
        
        # Config API must start first
        processes['config'] = Process(target=run_config_api_process)
        processes['config'].start()
        await asyncio.sleep(2)

        # Messaging API next
        processes['messaging'] = Process(target=run_messaging_api_process)
        processes['messaging'].start()
        await asyncio.sleep(1)

        # Communication API
        processes['communication'] = Process(target=run_communication_api_process)
        processes['communication'].start()
        await asyncio.sleep(1)

        # Start non-critical services
        logger.info("Starting non-critical services...")
        
        for service, runner in [
            ('process', run_process_api_process),
            ('state', run_state_api_process),
            ('data_collection', run_data_collection_api_process),
            ('validation', run_validation_api_process),
            ('ui', run_ui_process)
        ]:
            processes[service] = Process(target=runner)
            processes[service].start()
            await asyncio.sleep(1)

        def shutdown_handler(sig, frame):
            logger.info("Shutdown requested...")
            for name, process in processes.items():
                if process.is_alive():
                    logger.info(f"Stopping {name} service...")
                    process.terminate()
                    process.join(timeout=5.0)
                    if process.is_alive():
                        process.kill()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

        # Monitor processes
        while True:
            for name, process in processes.items():
                if not process.is_alive():
                    if name in CRITICAL_SERVICES:
                        logger.critical(f"Critical service {name} died - shutting down system")
                        shutdown_handler(None, None)
                    else:
                        logger.warning(f"Non-critical service {name} died - system continuing")
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
        # Clean shutdown
        for name, process in processes.items():
            if process.is_alive():
                logger.info(f"Stopping {name} service...")
                process.terminate()
                process.join()
        logger.info("Application shutdown complete")
        sys.exit(0)


# Add process runner functions for new services
def run_process_api_process():
    """Process function to run the Process API service."""
    uvicorn.run(
        "micro_cold_spray.api.process.router:app",
        host="0.0.0.0",
        port=8003,
        reload=True
    )


def run_state_api_process():
    """Process function to run the State API service."""
    uvicorn.run(
        "micro_cold_spray.api.state.router:app",
        host="0.0.0.0",
        port=8004,
        reload=True
    )


def run_data_collection_api_process():
    """Process function to run the Data Collection API service."""
    uvicorn.run(
        "micro_cold_spray.api.data_collection.router:app",
        host="0.0.0.0",
        port=8005,
        reload=True
    )


def run_validation_api_process():
    """Process function to run the Validation API service."""
    uvicorn.run(
        "micro_cold_spray.api.validation.router:app",
        host="0.0.0.0",
        port=8006,
        reload=True
    )


if __name__ == "__main__":
    asyncio.run(main())
