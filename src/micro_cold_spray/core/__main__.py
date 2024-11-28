"""Main application entry point."""
import sys
import asyncio
from pathlib import Path
from loguru import logger
from PySide6.QtWidgets import QApplication

from .config.config_manager import ConfigManager
from .infrastructure.messaging.message_broker import MessageBroker
from .infrastructure.tags.tag_manager import TagManager
from .infrastructure.state.state_manager import StateManager
from .components.ui.managers.ui_update_manager import UIUpdateManager
from .components.ui.windows.main_window import MainWindow

async def initialize_system() -> tuple[ConfigManager, MessageBroker, TagManager, StateManager]:
    """Initialize all system components."""
    logger.info("Starting system initialization")
    
    try:
        # Create message broker first
        message_broker = MessageBroker()
        await message_broker.start()
        
        # Create config manager with message broker
        config_manager = ConfigManager(message_broker)
        await config_manager.initialize()
        
        # Create tag manager with proper dependencies
        tag_manager = TagManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await tag_manager.initialize()
        
        # Test hardware connections before proceeding
        connection_status = await tag_manager.test_connections()
        if not any(connection_status.values()):
            logger.error("No hardware connections available")
            # Continue anyway, but warn the user
            await message_broker.publish("error", {
                "error": "No hardware connections available",
                "topic": "system/init",
                "details": connection_status
            })
        
        # Create state manager
        state_manager = StateManager(
            message_broker=message_broker,
            config_manager=config_manager
        )
        await state_manager.start()
        
        
        return config_manager, message_broker, tag_manager, state_manager
        
    except Exception as e:
        logger.exception("Failed to initialize system")
        raise SystemExit(f"System initialization failed: {e}")

def main() -> None:
    """Main application entry point."""
    try:
        # Initialize Qt application
        app = QApplication(sys.argv)
        
        # Run async initialization
        loop = asyncio.get_event_loop()
        config_manager, message_broker, tag_manager, state_manager = \
            loop.run_until_complete(initialize_system())
        
        # Create and show main window
        window = MainWindow(
            message_broker=message_broker,
            config_manager=config_manager,
            tag_manager=tag_manager,
            state_manager=state_manager
        )
        window.show()
        
        # Run event loop
        sys.exit(app.exec())
        
    except Exception as e:
        logger.exception("Application startup failed")
        sys.exit(f"Application startup failed: {e}")

if __name__ == "__main__":
    main() 