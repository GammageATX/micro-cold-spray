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


async def main():
    """Application entry point."""
    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")

        # Start Config API first since other services depend on it
        logger.info("Starting Config API service")
        config_api_process = Process(target=run_config_api_process)
        config_api_process.start()
        await asyncio.sleep(2)  # Give config service time to start

        # Start Messaging API next as communication depends on it
        logger.info("Starting Messaging API service")
        msg_api_process = Process(target=run_messaging_api_process)
        msg_api_process.start()
        await asyncio.sleep(1)  # Give messaging service time to start

        # Start Communication API after messaging is ready
        logger.info("Starting Communication API service")
        comm_api_process = Process(target=run_communication_api_process)
        comm_api_process.start()
        await asyncio.sleep(1)

        # Start UI last after all APIs are running
        logger.info("Starting UI service")
        ui_process = Process(target=run_ui_process)
        ui_process.start()

        # Create shutdown handler
        def shutdown_handler(sig, frame):
            logger.info("Shutdown requested...")
            for process in [ui_process, config_api_process,
                            comm_api_process, msg_api_process]:
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5.0)
                    if process.is_alive():
                        process.kill()
            sys.exit(0)

        signal.signal(signal.SIGINT, shutdown_handler)
        signal.signal(signal.SIGTERM, shutdown_handler)

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
        if 'config_api_process' in locals():
            config_api_process.terminate()
            config_api_process.join()
        if 'comm_api_process' in locals():
            comm_api_process.terminate()
            comm_api_process.join()
        if 'msg_api_process' in locals():
            msg_api_process.terminate()
            msg_api_process.join()
        logger.info("Application shutdown complete")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
