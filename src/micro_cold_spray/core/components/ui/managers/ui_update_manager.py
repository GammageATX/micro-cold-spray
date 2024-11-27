"""UI update manager component."""
from typing import Dict, Any, Optional, Set, List
from loguru import logger
import asyncio
from datetime import datetime
from enum import Enum
from PySide6.QtWidgets import QWidget

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager
from ....exceptions import UIError

class WidgetType(Enum):
    """Valid widget types."""
    WIDGET = "widget"
    TAB = "tab"
    CONTROL = "control"
    DISPLAY = "display"
    MONITOR = "monitor"

class WidgetLocation(Enum):
    """Valid widget locations."""
    MAIN = "main"
    DASHBOARD = "dashboard"
    MOTION = "motion"
    EDITOR = "editor"
    SYSTEM = "system"
    DIAGNOSTICS = "diagnostics"
    CONFIG = "config"

class UIUpdateManager:
    """Manages UI updates and widget registration."""
    
    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize with required dependencies."""
        if message_broker is None:
            logger.error("Cannot initialize UI update manager - no message broker provided")
            raise ValueError("MessageBroker is required")
        
        if config_manager is None:
            logger.error("Cannot initialize UI update manager - no config manager provided")
            raise ValueError("ConfigManager is required")
        
        self._message_broker = message_broker
        self._config_manager = config_manager
        
        # Widget registration tracking
        self._registered_widgets: Dict[str, Dict[str, Any]] = {}
        self._widget_id_registry: Dict[int, str] = {}
        self._tag_subscriptions: Dict[str, Set[str]] = {}
        self._is_initialized = False
        
        logger.info("UI update manager initialized")

    async def initialize(self) -> None:
        """Initialize UI update manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to relevant topics
            await self._message_broker.subscribe(
                "config/update/*",
                self._handle_config_update
            )
            await self._message_broker.subscribe(
                "config/status",
                self._handle_config_status
            )
            await self._message_broker.subscribe(
                "config/validation",
                self._handle_config_validation
            )
            
            self._is_initialized = True
            logger.info("UI update manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize UI update manager")
            raise UIError(f"UI update manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown UI update manager."""
        try:
            # Unregister all widgets
            for widget_id in list(self._registered_widgets.keys()):
                try:
                    await self.unregister_widget(widget_id)
                except Exception as e:
                    logger.error(f"Error unregistering widget {widget_id}: {e}")
            
            # Clear subscription tracking
            self._tag_subscriptions.clear()
            
            self._is_initialized = False
            logger.info("UI update manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during UI update manager shutdown")
            raise UIError(f"UI update manager shutdown failed: {str(e)}") from e

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle configuration updates from MessageBroker."""
        try:
            config_type = data.get("config_type")
            config_data = data.get("data", {})
            
            # Forward config update to relevant widgets
            await self.send_update(
                f"config.{config_type}",
                {
                    "type": config_type,
                    "data": config_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._message_broker.publish(
                "ui/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_config_status(self, data: Dict[str, Any]) -> None:
        """Handle configuration status updates."""
        try:
            await self.send_update(
                "config.status",
                {
                    "status": data,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling config status: {e}")

    async def _handle_config_validation(self, data: Dict[str, Any]) -> None:
        """Handle configuration validation results."""
        try:
            await self.send_update(
                "config.validation",
                {
                    "validation": data,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error handling config validation: {e}")

    async def register_widget(
        self,
        widget_id: str,
        update_tags: List[str],
        widget: Optional[QWidget] = None
    ) -> None:
        """Register a widget for updates."""
        try:
            # Check for duplicate registration
            if widget_id in self._registered_widgets:
                logger.warning(f"Widget {widget_id} already registered - updating tags")
                await self.unregister_widget(widget_id)
            
            # Store registration with metadata
            self._registered_widgets[widget_id] = {
                'tags': update_tags,
                'timestamp': datetime.now().isoformat(),
                'widget_ref': widget
            }
            
            # Update tag subscription tracking
            for tag in update_tags:
                if tag not in self._tag_subscriptions:
                    self._tag_subscriptions[tag] = set()
                self._tag_subscriptions[tag].add(widget_id)
                
            logger.debug(f"Registered widget {widget_id} for tags: {update_tags}")
            
            # Notify registration
            await self._message_broker.publish(
                "ui/widget/registered",
                {
                    "widget_id": widget_id,
                    "tags": update_tags,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error registering widget {widget_id}: {e}")
            raise UIError(f"Failed to register widget: {str(e)}") from e

    async def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget from updates."""
        try:
            if widget_id in self._registered_widgets:
                # Remove from tag subscriptions
                widget_tags = self._registered_widgets[widget_id]['tags']
                for tag in widget_tags:
                    if tag in self._tag_subscriptions:
                        self._tag_subscriptions[tag].discard(widget_id)
                        if not self._tag_subscriptions[tag]:
                            del self._tag_subscriptions[tag]
                
                # Remove registration
                del self._registered_widgets[widget_id]
                logger.debug(f"Unregistered widget {widget_id}")
                
                # Notify unregistration
                await self._message_broker.publish(
                    "ui/widget/unregistered",
                    {
                        "widget_id": widget_id,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error unregistering widget {widget_id}: {e}")
            raise UIError(f"Failed to unregister widget: {str(e)}") from e

    async def send_update(self, topic: str, data: Dict[str, Any]) -> None:
        """Send UI update via message broker."""
        try:
            await self._message_broker.publish(
                topic,
                {
                    **data,
                    "timestamp": datetime.now().isoformat()
                }
            )
        except Exception as e:
            logger.error(f"Error sending UI update: {e}")
            raise UIError(f"Failed to send UI update: {str(e)}") from e