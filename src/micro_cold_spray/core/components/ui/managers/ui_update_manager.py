"""UI update manager component."""
from typing import Dict, Any, Optional, Set, List
from loguru import logger
import asyncio
from datetime import datetime
from enum import Enum
from PySide6.QtWidgets import QWidget, QFrame
from PySide6.QtCore import Qt
from collections import defaultdict

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
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
        self._widgets: Dict[str, Dict[str, Any]] = {}
        self._tag_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._is_initialized = False
        logger.info("UI update manager initialized")

    async def initialize(self) -> None:
        """Initialize UI update manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to required topics
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            # Subscribe to all config update topics
            await self._message_broker.subscribe("config/update", self._handle_config_update)
            await self._message_broker.subscribe("config/update/hardware", self._handle_config_update)
            await self._message_broker.subscribe("config/update/process", self._handle_config_update)
            await self._message_broker.subscribe("config/update/ui", self._handle_config_update)
            
            self._is_initialized = True
            logger.info("UI update manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize UI update manager")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "initialization",
                "timestamp": datetime.now().isoformat()
            })
            raise UIError("Failed to initialize UI update manager") from e

    async def register_widget(
        self,
        widget_id: str,
        update_tags: List[str],
        widget_type: WidgetType,
        location: WidgetLocation,
        widget: Optional[QWidget] = None
    ) -> None:
        """Register a widget for updates."""
        try:
            # Verify widget has required async methods
            if widget:
                if not hasattr(widget, 'update') or not asyncio.iscoroutinefunction(widget.update):
                    raise UIError(f"Widget {widget_id} must implement async update() method")
                
                if not hasattr(widget, 'cleanup') or not asyncio.iscoroutinefunction(widget.cleanup):
                    raise UIError(f"Widget {widget_id} must implement async cleanup() method")
                
                # Verify Qt6 style usage
                self._verify_widget_style(widget)
            
            # Register widget with metadata
            self._widgets[widget_id] = {
                'widget': widget,
                'type': widget_type,
                'location': location,
                'tags': update_tags,
                'timestamp': datetime.now().isoformat()
            }
            
            # Update subscriptions
            for tag in update_tags:
                self._tag_subscriptions[tag].add(widget_id)
                
            # Notify registration
            await self._message_broker.publish("ui/widget/registered", {
                "widget_id": widget_id,
                "type": widget_type.value,
                "location": location.value,
                "tags": update_tags,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error registering widget {widget_id}: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "widget_registration",
                "widget_id": widget_id,
                "timestamp": datetime.now().isoformat()
            })
            raise UIError(f"Failed to register widget: {str(e)}") from e

    async def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget from updates."""
        try:
            if widget_id in self._widgets:
                # Call cleanup chain
                await self._cleanup_widget_chain(widget_id)
                
                # Remove subscriptions
                for tag in self._widgets[widget_id]['tags']:
                    self._tag_subscriptions[tag].discard(widget_id)
                    
                # Remove registration
                del self._widgets[widget_id]
                
                # Notify unregistration
                await self._message_broker.publish("ui/widget/unregistered", {
                    "widget_id": widget_id,
                    "timestamp": datetime.now().isoformat()
                })
                
        except Exception as e:
            logger.error(f"Error unregistering widget {widget_id}: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "widget_unregistration",
                "widget_id": widget_id,
                "timestamp": datetime.now().isoformat()
            })
            raise UIError(f"Failed to unregister widget: {str(e)}") from e

    def _verify_widget_style(self, widget: QWidget) -> None:
        """Verify widget uses proper Qt6 style constants."""
        if isinstance(widget, QFrame):
            if not isinstance(widget.frameShape(), QFrame.Shape):
                raise UIError("Must use QFrame.Shape.* for frame shapes")
            if not isinstance(widget.frameShadow(), QFrame.Shadow):
                raise UIError("Must use QFrame.Shadow.* for frame shadows")
                
        alignment = widget.alignment()
        if alignment and not isinstance(alignment, Qt.AlignmentFlag):
            raise UIError("Must use Qt.AlignmentFlag.* for alignments")

    async def _cleanup_widget_chain(self, widget_id: str) -> None:
        """Handle widget cleanup chain."""
        try:
            widget_data = self._widgets.get(widget_id)
            if not widget_data:
                return
                
            widget = widget_data.get('widget')
            if not widget:
                return
                
            # Clean up child widgets first
            for child in widget.findChildren(QWidget):
                if hasattr(child, 'cleanup'):
                    await child.cleanup()
                    
            # Clean up main widget
            await widget.cleanup()
            
        except Exception as e:
            logger.error(f"Error in widget cleanup chain: {e}")
            raise UIError(f"Widget cleanup chain failed: {str(e)}") from e

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates with proper async handling."""
        try:
            tag = data.get("tag")
            if not tag:
                raise ValueError("No tag in update data")
                
            # Update subscribed widgets with proper async handling
            update_tasks = []
            for widget_id in self._tag_subscriptions.get(tag, set()):
                widget = self._widgets[widget_id].get('widget')
                if widget and hasattr(widget, 'update'):
                    update_tasks.append(widget.update(data))
                    
            # Wait for all updates to complete
            if update_tasks:
                await asyncio.gather(*update_tasks)
                    
        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "tag_update_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle config updates."""
        try:
            # Forward config update to UI
            await self._message_broker.publish("ui/update", {
                "type": "config",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "config_update_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def shutdown(self) -> None:
        """Shutdown UI update manager."""
        try:
            # Cleanup all registered widgets
            for widget_id in list(self._widgets.keys()):
                await self.unregister_widget(widget_id)
                
            self._is_initialized = False
            logger.info("UI update manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during UI update manager shutdown")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "shutdown",
                "timestamp": datetime.now().isoformat()
            })
            raise UIError("Failed to shutdown UI update manager") from e