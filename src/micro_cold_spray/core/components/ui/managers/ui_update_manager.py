"""UI update manager component."""
from typing import Dict, Any, Optional, Set, List
from loguru import logger
from datetime import datetime
from enum import Enum
from PySide6.QtWidgets import QWidget, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from collections import defaultdict

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ....exceptions import UIError, CoreError, ValidationError


class WidgetType(Enum):
    """Valid widget types."""
    WIDGET = "widget"
    TAB = "tab"
    CONTROL = "control"
    DISPLAY = "display"
    MONITOR = "monitor"


class WidgetLocation(Enum):
    """Valid widget locations."""
    DASHBOARD = "dashboard"
    SYSTEM = "system"


class UIUpdateManager:
    """Manages UI updates and widget registration."""

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._registered_widgets: Dict[str, Dict[str, Any]] = {}
        self._tag_subscriptions: Dict[str, Set[str]] = defaultdict(set)
        self._is_initialized = False
        logger.info("UI update manager initialized")

    async def register_widget(
        self,
        widget_id: str,
        update_tags: List[str],
        widget: Optional[QWidget] = None
    ) -> None:
        """Register a widget for updates."""
        try:
            # Validate widget location
            parts = widget_id.split('_')
            if len(parts) < 2:
                raise ValidationError("Invalid widget ID format")

            widget_location = parts[1]
            if (
                widget_location != WidgetLocation.DASHBOARD.value
                and widget_location != WidgetLocation.SYSTEM.value
            ):
                raise ValidationError(
                    "Only dashboard and system widgets are currently supported", {
                        "widget_id": widget_id, "location": widget_location})

            # Rest of the existing registration code...
            if widget_id in self._registered_widgets:
                logger.warning(
                    f"Widget {widget_id} already registered - updating tags")
                await self.unregister_widget(widget_id)

            if widget:
                self._verify_widget_style(widget)

            self._registered_widgets[widget_id] = {
                'tags': update_tags,
                'timestamp': datetime.now().isoformat(),
                'widget_ref': widget
            }

            for tag in update_tags:
                self._tag_subscriptions[tag].add(widget_id)

            logger.debug(
                f"Registered dashboard widget {widget_id} for tags: {update_tags}")

            await self._message_broker.publish(
                "ui/widget/registered",
                {
                    "widget_id": widget_id,
                    "tags": update_tags,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except ValidationError as e:
            logger.error(f"Widget validation failed for {widget_id}: {e}")
            raise
        except Exception as e:
            error_msg = f"Failed to register widget {widget_id}: {str(e)}"
            logger.error(error_msg)
            raise UIError(error_msg) from e

    async def initialize(self) -> None:
        """Initialize UI update manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to required topics
            subscriptions = [
                ("tag/update", self._handle_tag_update),
                ("config/update", self._handle_config_update),
                ("config/update/hardware", self._handle_hardware_config_update),
                ("config/update/process", self._handle_config_update),
                ("config/update/ui", self._handle_config_update),
                ("sequence/loaded", self._handle_sequence_loaded),
                ("sequence/state", self._handle_sequence_state)
            ]

            for topic, handler in subscriptions:
                await self._message_broker.subscribe(topic, handler)

            # Load initial hardware config
            hardware_config = await self._config_manager.get_config("hardware")
            self._stage_dimensions = hardware_config.get(
                "stage", {}).get("dimensions", {})

            self._is_initialized = True
            logger.info("UI update manager initialization complete")

        except Exception as e:
            logger.exception("Failed to initialize UI update manager")
            raise CoreError("Failed to initialize UI update manager", {
                "error": str(e)
            })

    async def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget from updates."""
        try:
            if widget_id in self._registered_widgets:
                # Call cleanup chain
                await self._cleanup_widget_chain(widget_id)

                # Remove subscriptions
                for tag in self._registered_widgets[widget_id]['tags']:
                    self._tag_subscriptions[tag].discard(widget_id)

                # Remove registration
                del self._registered_widgets[widget_id]

                # Notify unregistration
                await self._message_broker.publish("ui/widget/unregistered", {
                    "widget_id": widget_id,
                    "timestamp": datetime.now().isoformat()
                })

        except Exception as e:
            logger.error(f"Error unregistering widget {widget_id}: {e}")
            raise CoreError("Failed to unregister widget", {
                "widget_id": widget_id,
                "error": str(e)
            })

    def _verify_widget_style(self, widget: QWidget) -> None:
        """Verify widget uses proper Qt6 style constants."""
        # Only verify QFrame style constants
        if isinstance(widget, QFrame):
            if not isinstance(widget.frameShape(), QFrame.Shape):
                raise ValidationError(
                    "Must use QFrame.Shape.* for frame shapes")
            if not isinstance(widget.frameShadow(), QFrame.Shadow):
                raise ValidationError(
                    "Must use QFrame.Shadow.* for frame shadows")

            # Check layout alignment if widget has a layout
            if widget.layout():
                layout_alignment = widget.layout().alignment()
                if layout_alignment and not isinstance(
                        layout_alignment, Qt.AlignmentFlag):
                    raise ValidationError(
                        "Must use Qt.AlignmentFlag.* for alignments")

            h_policy = widget.sizePolicy().horizontalPolicy()
            v_policy = widget.sizePolicy().verticalPolicy()
            if not isinstance(h_policy, QSizePolicy.Policy) or \
               not isinstance(v_policy, QSizePolicy.Policy):
                raise ValidationError(
                    "Must use QSizePolicy.Policy.* for size policies")

    async def _cleanup_widget_chain(self, widget_id: str) -> None:
        """Handle widget cleanup chain."""
        try:
            widget_data = self._registered_widgets.get(widget_id)
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
            raise CoreError("Widget cleanup chain failed", {
                "widget_id": widget_id,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag updates."""
        try:
            tag = data.get("tag")
            value = data.get("value")

            if tag and value is not None:
                # Forward as UI update
                await self.send_update(
                    tag,
                    {
                        "value": value,
                        "timestamp": datetime.now().isoformat()
                    }
                )

                # Special handling for connection status
                if tag in ["hardware.plc.connected", "hardware.ssh.connected"]:
                    await self.send_update(
                        "system.connection",
                        {
                            "connected": value,
                            "source": tag,
                            "timestamp": datetime.now().isoformat()
                        }
                    )

                logger.debug(f"Processed tag update: {tag}={value}")

        except Exception as e:
            logger.error(f"Error handling tag update: {e}")

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

    async def _handle_hardware_config_update(
            self, data: Dict[str, Any]) -> None:
        """Handle hardware configuration updates."""
        try:
            if "stage" in data:
                self._stage_dimensions = data["stage"].get("dimensions", {})

            # Forward hardware config update to UI
            await self._message_broker.publish("ui/update/hardware", {
                "type": "hardware_config",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error handling hardware config update: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "hardware_config_update",
                "timestamp": datetime.now().isoformat()
            })

    def get_stage_dimensions(self) -> Dict[str, float]:
        """Get stage dimensions from hardware config.

        Returns:
            Dict containing x, y, z dimensions of the stage
        """
        return self._stage_dimensions

    async def shutdown(self) -> None:
        """Shutdown UI update manager."""
        try:
            # Cleanup all registered widgets
            for widget_id in list(self._registered_widgets.keys()):
                await self.unregister_widget(widget_id)

            self._is_initialized = False
            logger.info("UI update manager shutdown complete")

        except Exception as e:
            logger.exception("Error during UI update manager shutdown")
            raise CoreError("Failed to shutdown UI update manager", {
                "error": str(e)
            })

    async def send_update(self, topic: str, data: Dict[str, Any]) -> None:
        """Send UI update via message broker.

        Args:
            topic: Topic to publish update to
            data: Update data or string message

        Raises:
            UIError: If update fails
        """
        try:
            # Convert string messages to proper format
            if isinstance(data, str):
                data = {
                    "message": data,
                    "timestamp": datetime.now().isoformat()
                }
            elif isinstance(data, dict) and 'timestamp' not in data:
                data['timestamp'] = datetime.now().isoformat()

            # Forward update through message broker
            await self._message_broker.publish(
                f"ui/update/{topic}",
                data
            )

            # Also publish to original topic for other subscribers
            await self._message_broker.publish(
                topic,
                data
            )

            logger.debug(f"Sent update on topic {topic}: {data}")

        except Exception as e:
            logger.error(f"Error sending UI update: {e}")
            raise UIError(f"Failed to send UI update: {str(e)}") from e

    async def _handle_system_state(self, data: Dict[str, Any]) -> None:
        """Handle system state updates."""
        try:
            state = data.get("state", "DISCONNECTED")

            # Forward state update to all registered widgets
            await self.send_update(
                "system.state",
                {
                    "state": state,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Also send connection status update
            await self.send_update(
                "system.connection",
                {
                    "connected": state != "DISCONNECTED",
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling system state: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "system_state_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_sequence_state(self, data: Dict[str, Any]) -> None:
        """Handle sequence state updates."""
        try:
            if not self._is_initialized:
                return

            state = data.get("state")
            if state == "STARTING" and not await self._check_connection():
                # Block sequence start if disconnected
                error_msg = (
                    "Cannot start sequence in disconnected state - "
                    "please connect hardware first"
                )
                await self.send_update(
                    "system.message",
                    {
                        "message": error_msg,
                        "level": "warning",
                        "timestamp": datetime.now().isoformat()
                    }
                )
                return

            # Update data collection state based on sequence state
            if state == "RUNNING":
                await self.send_update(
                    "data.collection.state",
                    {
                        "state": "COLLECTING",
                        "timestamp": datetime.now().isoformat()
                    }
                )
            elif state in ["COMPLETED", "CANCELLED", "ERROR"]:
                await self.send_update(
                    "data.collection.state",
                    {
                        "state": "STOPPED",
                        "timestamp": datetime.now().isoformat()
                    }
                )

            # Forward sequence state update
            await self.send_update(
                "sequence.state",
                {
                    "state": state,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "sequence_state_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def _check_connection(self) -> bool:
        """Check if system is connected to hardware."""
        try:
            state = await self._message_broker.request(
                "system/state",
                {
                    "timestamp": datetime.now().isoformat()
                },
                timeout=1.0
            )
            return state.get("state") == "CONNECTED"
        except Exception:
            return False

    async def _handle_sequence_loaded(self, data: Dict[str, Any]) -> None:
        """Handle sequence loaded events."""
        try:
            logger.debug(f"Handling sequence loaded event: {data}")

            # Send sequence loaded notification to all subscribed widgets
            for widget_id in self._tag_subscriptions.get(
                    "sequence.loaded", set()):
                widget = self._registered_widgets[widget_id].get('widget_ref')
                if widget and hasattr(widget, 'handle_ui_update'):
                    await widget.handle_ui_update({
                        "sequence.loaded": data
                    })

            # Also send through general update mechanism
            await self.send_update(
                "sequence.loaded",
                data
            )

            logger.debug(
                f"Sequence loaded event handled: {
                    data.get(
                        'name',
                        'unnamed')}")

        except Exception as e:
            logger.error(f"Error handling sequence loaded: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "sequence_loaded_handler",
                "timestamp": datetime.now().isoformat()
            })

    def _validate_widget(self, widget_id: str) -> bool:
        """Validate widget registration."""
        allowed_prefixes = [
            'widget_dashboard_',
            'tab_dashboard',
            'widget_system_'  # Add this to allow system widgets
        ]
        return any(widget_id.startswith(prefix) for prefix in allowed_prefixes)
