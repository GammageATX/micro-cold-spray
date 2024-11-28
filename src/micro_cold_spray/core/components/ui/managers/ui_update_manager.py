"""UI update manager component."""
from typing import Dict, Any, Optional, Set, List
from loguru import logger
import asyncio
from datetime import datetime
from enum import Enum
from PySide6.QtWidgets import QWidget
from collections import defaultdict

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
        self._tag_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._running = False
        self._processing_task: asyncio.Task | None = None
        
        logger.info("UI update manager initialized")

    async def start(self) -> None:
        """Start the UI update manager."""
        try:
            if self._running:
                logger.warning("UI update manager already running")
                return

            self._running = True
            
            # Subscribe to config updates
            await self._message_broker.subscribe("config/update/*", self._handle_config_update)
            # Subscribe to tag updates
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            
            # Start processing task if needed
            if not self._processing_task:
                self._processing_task = asyncio.create_task(self._process_updates())
            
            logger.info("UI update manager started")

        except Exception as e:
            logger.exception("Failed to start UI update manager")
            raise UIError("Failed to start UI update manager") from e

    async def shutdown(self) -> None:
        """Shutdown the UI update manager."""
        try:
            logger.info("Shutting down UI update manager")
            self._running = False
            
            if self._processing_task:
                self._processing_task.cancel()
                try:
                    await self._processing_task
                except asyncio.CancelledError:
                    pass
                self._processing_task = None

            # Clear registrations
            self._registered_widgets.clear()
            self._tag_subscriptions.clear()
            
            logger.info("UI update manager shutdown complete")

        except Exception as e:
            logger.exception("Error during UI update manager shutdown")
            raise UIError("Failed to shutdown UI update manager") from e

    async def _process_updates(self) -> None:
        """Process UI updates."""
        try:
            while self._running:
                try:
                    await asyncio.sleep(0.1)  # Prevent tight loop
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in update processing: {e}")
                    await asyncio.sleep(1.0)  # Longer pause on error

        except asyncio.CancelledError:
            logger.info("Update processing cancelled")
            raise
        except Exception as e:
            logger.exception("Fatal error in update processing")
            raise UIError("Update processing failed") from e

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle configuration updates from MessageBroker.
        
        Args:
            data: Configuration update data containing config_type and data
        """
        try:
            config_type = data.get("config_type")
            config_data = data.get("data", {})
            
            # Forward config update to UI components
            await self.send_update(
                "ui/update",  # This matches the test's subscription
                {
                    "type": "config",  # Indicate this is a config update
                    "config_type": config_type,
                    "data": config_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.debug(f"Forwarded config update for type {config_type}")
            
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "error": str(e),
                    "topic": "config/update",
                    "data": data
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

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates from MessageBroker.
        
        Args:
            data: Tag update data containing tag name and value
        """
        try:
            tag = data.get("tag")
            value = data.get("value")
            
            if tag is None:
                logger.error("Received tag update without tag name")
                return
            
            # Find widgets subscribed to this tag
            if tag in self._tag_subscriptions:
                for widget_id in self._tag_subscriptions[tag]:
                    if widget_id in self._registered_widgets:
                        widget = self._registered_widgets[widget_id]
                        if hasattr(widget, 'update'):
                            try:
                                await widget.update(tag, value)
                            except Exception as e:
                                logger.error(f"Error updating widget {widget_id} for tag {tag}: {e}")
                                await self._message_broker.publish(
                                    "error",
                                    {
                                        "error": str(e),
                                        "topic": "tag/update",
                                        "widget": widget_id,
                                        "tag": tag,
                                        "value": value
                                    }
                                )
                        else:
                            logger.warning(f"Widget {widget_id} has no update method")
                    else:
                        logger.warning(f"Widget {widget_id} subscribed to tag {tag} but not registered")
                    
        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "error": str(e),
                    "topic": "tag/update",
                    "data": data
                }
            )