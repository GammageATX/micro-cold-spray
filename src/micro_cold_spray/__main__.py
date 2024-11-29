# src/micro_cold_spray/__main__.py
import sys
import asyncio
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import QApplication, QProgressDialog
from PySide6.QtCore import Qt
import yaml

from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.infrastructure.state.state_manager import StateManager
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.components.ui.windows.main_window import MainWindow
from micro_cold_spray.core.exceptions import SystemInitializationError

def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    return Path(__file__).parent.parent.parent

def setup_logging() -> None:
    """Configure loguru for application logging."""
    logger.remove()  # Remove default handler
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
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
        "data/parameters/library/materials",
        "data/parameters/library/process",
        "data/parameters/history",
        "data/patterns/library",
        "data/patterns/custom",
        "data/patterns/history",
        "data/sequences/library",
        "data/sequences/history",
        "data/runs",
        "logs",
        "resources"
    ]
    
    for directory in directories:
        (project_root / directory).mkdir(parents=True, exist_ok=True)

class SplashScreen(QProgressDialog):
    """Splash screen for initialization."""
    def __init__(self):
        super().__init__("Initializing System...", None, 0, 0)
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

async def initialize_system() -> tuple[ConfigManager, MessageBroker, TagManager, StateManager, UIUpdateManager]:
    """Initialize all system components."""
    logger.info("Starting system initialization")
    
    try:
        # Create message broker first
        logger.debug("Initializing MessageBroker")
        message_broker = MessageBroker()
        await message_broker.start()
        
        # Create config manager with message broker
        logger.debug("Initializing ConfigManager")
        config_manager = ConfigManager(message_broker)
        await config_manager.initialize()
        
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
            logger.error("No hardware connections available")
            await message_broker.publish("error", {
                "error": "No hardware connections available",
                "topic": "system/init",
                "details": connection_status
            })
        
        # Create and initialize state manager
        logger.debug("Initializing StateManager")
        state_manager = StateManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await state_manager.initialize()
        
        # Create and initialize UI manager
        logger.debug("Initializing UIUpdateManager")
        ui_manager = UIUpdateManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await ui_manager.initialize()
        
        logger.info("System initialization complete")
        return config_manager, message_broker, tag_manager, state_manager, ui_manager
        
    except Exception as e:
        logger.exception("Critical error during system initialization")
        raise SystemInitializationError(f"Failed to initialize system: {str(e)}") from e

async def main() -> None:
    """Application entry point with proper cleanup chains."""
    app = None
    system_components = None
    window = None
    
    try:
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application")
        
        app = QApplication(sys.argv)
        
        # Show splash screen
        splash = SplashScreen()
        splash.show()
        app.processEvents()
        
        # Initialize system
        splash.setLabelText("Initializing System Components...")
        app.processEvents()
        system_components = await initialize_system()
        config_manager, message_broker, tag_manager, state_manager, ui_manager = system_components
        
        # Create and initialize main window
        splash.setLabelText("Initializing User Interface...")
        app.processEvents()
        window = MainWindow(
            config_manager=config_manager,
            message_broker=message_broker,
            ui_manager=ui_manager,
            tag_manager=tag_manager,
            state_manager=state_manager
        )
        await window.initialize()
        
        # Show main window and close splash
        splash.close()
        window.show()
        
        while not window.is_closing:
            app.processEvents()
            await asyncio.sleep(0.01)
            if not window.isVisible():
                break
                
    except Exception as e:
        logger.exception("Critical application error")
        raise
    finally:
        # Proper cleanup chain
        try:
            if system_components:
                config_manager, message_broker, tag_manager, state_manager, ui_manager = system_components
                
                logger.info("Shutting down system components")
                await ui_manager.shutdown()
                await state_manager.shutdown()
                await tag_manager.shutdown()
                await message_broker.shutdown()
                
            if app:
                logger.info("Shutting down Qt application")
                app.quit()
                app.processEvents()
                
        except Exception as e:
            logger.exception("Error during cleanup")
        finally:
            logger.info("Application shutdown complete")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())