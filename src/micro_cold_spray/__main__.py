# src/micro_cold_spray/__main__.py
import asyncio
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QProgressDialog

from micro_cold_spray.core.ui.managers.ui_update_manager import (
    UIUpdateManager,
)
from micro_cold_spray.core.ui.windows.main_window import MainWindow
from micro_cold_spray.core.exceptions import ConfigurationError, CoreError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.process.data.data_manager import DataManager

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


class SplashScreen(QProgressDialog):
    """Splash screen for initialization."""

    def __init__(self):
        super().__init__(
            "Initializing System...",
            "",  # Empty string instead of None for cancelButtonText
            0,
            0
        )
        self.setWindowTitle("Micro Cold Spray")
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAutoClose(True)
        self.setAutoReset(True)
        self.setMinimumDuration(0)
        self.setStyleSheet("""
            QProgressDialog {
                background-color: #f5f5f5;
                border: 1px solid #cccccc;
                border-radius: 4px;
                padding: 20px;
            }
            QLabel {
                color: #2c3e50;
                font-size: 12px;
            }
            QProgressBar {
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #3498db;
            }
        """)


async def initialize_system() -> tuple[
    ConfigManager,
    MessageBroker,
    TagManager,
    StateManager,
    UIUpdateManager,
    DataManager
]:
    """Initialize all system components."""
    logger.info("Starting system initialization")

    try:
        # Create message broker first
        logger.debug("Initializing MessageBroker")
        message_broker = MessageBroker()
        await message_broker.initialize()

        # Create config manager with proper path and message broker
        logger.debug("Initializing ConfigManager")
        config_path = get_project_root() / "config"
        config_manager = ConfigManager(config_path, message_broker)
        await config_manager.initialize()

        # Update message broker with config topics
        logger.debug("Updating MessageBroker with config topics")
        app_config = await config_manager.get_config("application")
        if "services" in app_config.get("application", {}) and \
           "message_broker" in app_config["application"]["services"] and \
           "topics" in app_config["application"]["services"]["message_broker"]:
            topics_config = app_config["application"]["services"]["message_broker"]["topics"]
            config_topics = set()
            for topic_group in topics_config.values():
                if isinstance(topic_group, list):
                    config_topics.update(topic_group)
            await message_broker.update_from_config(config_topics)

        # Create tag manager with proper dependencies
        logger.debug("Initializing TagManager")
        tag_manager = TagManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await tag_manager.initialize()

        # Test hardware connections
        connection_status = await tag_manager.test_connections()
        if not any(connection_status.values()):
            logger.warning(
                "No hardware connections available - starting in disconnected mode")
            await message_broker.publish("system/status", {
                "status": "disconnected",
                "details": connection_status,
                "timestamp": datetime.now().isoformat()
            })

        # Create and initialize state manager
        logger.debug("Initializing StateManager")
        state_manager = StateManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await state_manager.initialize()

        # Create and initialize data manager
        logger.debug("Initializing DataManager")
        data_manager = DataManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await data_manager.initialize()

        # Create UI manager (simplified version)
        logger.debug("Initializing UIUpdateManager")
        ui_manager = UIUpdateManager()

        # Subscribe tag manager to handle tag updates
        await tag_manager.subscribe_ui_manager(ui_manager)

        logger.info("System initialization complete")
        return config_manager, message_broker, tag_manager, state_manager, ui_manager, data_manager

    except Exception as e:
        error_msg = {
            "error": str(e),
            "context": "system_initialization",
            "timestamp": datetime.now().isoformat()
        }
        logger.exception(
            f"Critical error during system initialization: {error_msg}")
        raise CoreError("Failed to initialize system", error_msg) from e


async def main() -> None:
    """Application entry point with proper cleanup chains."""
    app = None
    system_components = None
    window = None

    try:
        setup_logging()
        ensure_directories()
        logger.info(
            "Starting Micro Cold Spray application - Dashboard Only Mode")

        app = QApplication(sys.argv)

        # Show splash screen
        splash = SplashScreen()
        splash.show()
        app.processEvents()

        # Initialize system
        splash.setLabelText("Initializing System Components...")
        app.processEvents()
        system_components = await initialize_system()
        config_manager, message_broker, tag_manager, state_manager, ui_manager, data_manager = system_components

        # Create and initialize main window
        splash.setLabelText("Initializing Dashboard Interface...")
        app.processEvents()

        # Get UI config
        app_config = await config_manager.get_config("application")
        if "window" not in app_config:
            raise ConfigurationError(
                "Missing window configuration in application.yaml")

        window = MainWindow(
            config_manager=config_manager,
            message_broker=message_broker,
            ui_manager=ui_manager,
            tag_manager=tag_manager,
            ui_config=app_config["window"]
        )
        await window.initialize()

        # Show main window and close splash
        splash.close()
        window.show()

        # Main event loop
        while True:
            app.processEvents()
            await asyncio.sleep(0.01)
            
            # Check if window is closing or closed
            if window.is_closing or not window.isVisible():
                # Wait for any pending cleanup tasks
                await asyncio.sleep(0.1)  # Give cleanup tasks time to complete
                break

    except Exception as e:
        error_msg = {
            "error": str(e),
            "context": "main_execution",
            "timestamp": datetime.now().isoformat()
        }
        logger.exception(f"Critical application error: {error_msg}")
        if 'message_broker' in locals() and message_broker:
            try:
                await message_broker.publish("error", error_msg)
            except Exception as publish_error:
                logger.error(
                    f"Failed to publish error message: {publish_error}")
        raise
    finally:
        # Proper cleanup chain
        try:
            if system_components:
                (
                    config_manager,
                    message_broker,
                    tag_manager,
                    state_manager,
                    ui_manager,
                    data_manager
                ) = system_components

                logger.info("Shutting down system components")
                try:
                    await state_manager.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down state manager: {e}")
                try:
                    await tag_manager.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down tag manager: {e}")
                try:
                    await data_manager.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down data manager: {e}")
                try:
                    await message_broker.shutdown()
                except Exception as e:
                    logger.error(f"Error shutting down message broker: {e}")

            if app:
                logger.info("Shutting down Qt application")
                app.quit()
                app.processEvents()

        except Exception as e:
            error_msg = {
                "error": str(e),
                "context": "shutdown",
                "timestamp": datetime.now().isoformat()
            }
            logger.exception(f"Error during cleanup: {error_msg}")
        finally:
            logger.info("Application shutdown complete")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
