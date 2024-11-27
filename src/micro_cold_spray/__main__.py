# src/micro_cold_spray/__main__.py
import sys
import asyncio
import logging
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager
from micro_cold_spray.core.components.ui.windows.main_window import MainWindow
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

def get_project_root() -> Path:
    """Get the absolute path to the project root directory."""
    # Assuming this file is in src/micro_cold_spray/__main__.py
    return Path(__file__).parent.parent.parent

def setup_logging() -> None:
    """Configure basic logging for development."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
        ]
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

async def initialize_minimal_system() -> tuple[ConfigManager, MessageBroker, TagManager, UIUpdateManager]:
    """Initialize minimal system components."""
    try:
        # Create message broker first
        message_broker = MessageBroker()
        if message_broker is None:
            raise ValueError("Failed to create MessageBroker")
        
        # Create config manager with message broker
        config_manager = ConfigManager(message_broker)
        if config_manager is None:
            raise ValueError("Failed to create ConfigManager")
        
        # Create tag manager
        tag_manager = TagManager()
        if tag_manager is None:
            raise ValueError("Failed to create TagManager")
            
        tag_manager.set_message_broker(message_broker)
        tag_manager.load_config(config_manager)
        
        # Create and start UI manager
        ui_manager = UIUpdateManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        if ui_manager is None:
            raise ValueError("Failed to create UIUpdateManager")
            
        await ui_manager.start()
        
        return config_manager, message_broker, tag_manager, ui_manager
        
    except Exception as e:
        logger.error(f"Error initializing system: {e}")
        raise

async def initialize_system():
    config_manager = ConfigManager()
    message_broker = MessageBroker()
    tag_manager = TagManager(config_manager, message_broker)
    # Other initializations...

async def main() -> None:
    """Minimal application entry point."""
    app = None
    try:
        # Setup logging
        setup_logging()
        ensure_directories()
        logger.info("Starting Micro Cold Spray application (Minimal Version)")
        
        # Create QApplication
        app = QApplication(sys.argv)
        
        # Initialize minimal system
        config_manager, message_broker, tag_manager, ui_manager = await initialize_minimal_system()
        
        # Create and show main window with all dependencies
        window = MainWindow(
            config_manager=config_manager,
            message_broker=message_broker,
            ui_manager=ui_manager,
            tag_manager=tag_manager
        )
        window.show()
        
        # Use the asyncio event loop to process Qt events and UI updates
        while not window.is_closing:
            app.processEvents()
            await asyncio.sleep(0.01)  # Allow other coroutines to run
            
            # Check if window was closed
            if not window.isVisible():
                break
        
        logger.info("Application shutdown initiated")
            
    except asyncio.CancelledError:
        logger.info("Application cancelled")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        try:
            # Clean shutdown sequence
            if app:
                app.quit()
                app.processEvents()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        finally:
            logger.info("Application shutdown complete")
            sys.exit(0)

if __name__ == "__main__":
    asyncio.run(initialize_system())