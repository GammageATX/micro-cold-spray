"""UI update manager component."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QSizePolicy, QWidget, QLabel

from ....exceptions import CoreError, UIError, ValidationError
from ....infrastructure.config.config_manager import ConfigManager
from ....infrastructure.messaging.message_broker import MessageBroker
from ..widgets.base_widget import BaseWidget


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
    MOTION = "motion"
    EDITOR = "editor"
    CONFIG = "config"
    DIAGNOSTICS = "diagnostics"


class UIUpdateManager:
    """Manager for coordinating UI updates and widget registration."""

    # Valid widget types and locations
    VALID_TYPES = {
        'widget',        # Generic widgets
        'tab',          # Tab containers
        'control',      # Control widgets
        'display',      # Display widgets
    }

    VALID_LOCATIONS = {
        'system',       # System-level widgets
        'dashboard',    # Dashboard tab widgets
        'motion',       # Motion control tab widgets
        'editor',       # Sequence editor tab widgets
        'config',       # Configuration tab widgets
        'diagnostics',  # Diagnostics tab widgets
    }

    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ) -> None:
        """Initialize UI update manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._widgets: Dict[str, BaseWidget] = {}
        self._tag_subscriptions: Dict[str, Set[str]] = {}
        self._stage_dimensions: Dict[str, float] = {}
        self._is_initialized = False

        logger.debug("UI update manager initialized")

    async def initialize(self) -> None:
        """Initialize UI update manager."""
        try:
            if self._is_initialized:
                return

            # Subscribe to required topics
            await self._message_broker.subscribe("ui/update", self._handle_ui_update)
            await self._message_broker.subscribe("ui/error", self._handle_ui_error)
            await self._message_broker.subscribe("config/response/list_files", self._handle_list_files_response)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            await self._message_broker.subscribe("config/update", self._handle_config_update)
            await self._message_broker.subscribe("config/update/hardware", self._handle_hardware_config_update)
            await self._message_broker.subscribe("config/update/process", self._handle_config_update)
            await self._message_broker.subscribe("config/update/ui", self._handle_config_update)
            await self._message_broker.subscribe("sequence/loaded", self._handle_sequence_loaded)
            await self._message_broker.subscribe("sequence/state", self._handle_sequence_state)

            # Load initial hardware config
            hardware_config = await self._config_manager.get_config("hardware")
            self._stage_dimensions = hardware_config.get(
                "stage", {}).get("dimensions", {})

            self._is_initialized = True
            logger.debug("UI update manager initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize UI update manager: {e}")
            raise UIError("UI update manager initialization failed") from e

    async def _handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI update messages."""
        try:
            update_type = data.get("type")
            update_data = data.get("data", {})

            if not update_type:
                raise ValueError("No update type specified")

            # Find widgets that need this update
            for widget_id, widget in self._widgets.items():
                if hasattr(widget, "handle_ui_update"):
                    await widget.handle_ui_update(update_data)

            logger.debug(f"Processed UI update: {update_type}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "ui_update_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_ui_error(self, data: Dict[str, Any]) -> None:
        """Handle UI error messages."""
        try:
            error = data.get("error")
            context = data.get("context", "unknown")

            logger.error(f"UI error in {context}: {error}")

            # Notify widgets of error
            for widget in self._widgets.values():
                if hasattr(widget, "handle_error"):
                    await widget.handle_error(data)

        except Exception as e:
            logger.error(f"Error handling UI error: {e}")

    def _validate_widget_location(self, location: str) -> bool:
        """Validate widget location against allowed values."""
        allowed_prefixes = [
            "widget_dashboard",
            "widget_motion",
            "widget_editor",
            "widget_config",
            "widget_diagnostics",
            "tab_dashboard",
            "tab_motion",
            "tab_editor",
            "tab_config",
            "tab_diagnostics"
        ]
        return any(location.startswith(prefix) for prefix in allowed_prefixes)

    async def register_widget(
        self,
        widget_id: str,
        update_tags: List[str],
        widget: Optional[QWidget] = None
    ) -> None:
        """Register a widget for tag updates."""
        try:
            # Validate widget ID format and location
            parts = widget_id.split('_')
            if len(parts) < 2:
                raise ValidationError(
                    f"Invalid widget ID format: {widget_id}. Expected format: type_location_name"
                )

            widget_type, location = parts[0], parts[1]
            if widget_type not in self.VALID_TYPES:
                raise ValidationError(
                    f"Invalid widget type: {widget_type}. Must be one of: {self.VALID_TYPES}"
                )
            if location not in self.VALID_LOCATIONS:
                raise ValidationError(
                    f"Invalid widget location: {location}. Must be one of: {self.VALID_LOCATIONS}"
                )

            # Validate widget style if provided
            if widget:
                self._verify_widget_style(widget)

            # Update registrations
            if widget_id in self._widgets:
                old_tags = self._widgets[widget_id]['tags']
                new_tags = set(update_tags)
                added_tags = new_tags - set(old_tags)
                removed_tags = set(old_tags) - new_tags

                if added_tags or removed_tags:
                    logger.debug(
                        f"Updating tags for {widget_id}:\n"
                        f"  Added: {added_tags if added_tags else 'none'}\n"
                        f"  Removed: {removed_tags if removed_tags else 'none'}"
                    )

            # Store registration
            self._widgets[widget_id] = {
                'tags': update_tags,
                'timestamp': datetime.now().isoformat(),
                'widget_ref': widget
            }

            # Update tag subscriptions
            for tag in update_tags:
                if tag not in self._tag_subscriptions:
                    self._tag_subscriptions[tag] = set()
                self._tag_subscriptions[tag].add(widget_id)

            logger.debug(f"Registered widget {widget_id} with {len(update_tags)} tags")

        except Exception as e:
            logger.error(f"Failed to register widget {widget_id}: {str(e)}")
            raise UIError(f"Widget registration failed: {str(e)}") from e

    async def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget from updates."""
        try:
            if widget_id in self._widgets:
                # Remove subscriptions
                for tag in self._widgets[widget_id]['tags']:
                    if tag in self._tag_subscriptions:
                        self._tag_subscriptions[tag].discard(widget_id)

                # Remove registration
                widget_data = self._widgets[widget_id]
                del self._widgets[widget_id]

                # Clean up widget if it exists
                widget = widget_data.get('widget_ref')
                if widget and hasattr(widget, '_cleanup_resources'):
                    try:
                        await widget._cleanup_resources()
                    except Exception as e:
                        logger.error(f"Error cleaning up widget resources: {e}")

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
        # Check QLabel alignment
        if isinstance(widget, QLabel):
            alignment = widget.alignment()
            if not isinstance(alignment, Qt.AlignmentFlag):
                raise ValidationError(
                    "Must use Qt.AlignmentFlag.* for alignments")

        # Check QFrame style constants
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
            widget_data = self._widgets.get(widget_id)
            if not widget_data:
                return

            widget = widget_data.get('widget_ref')
            if not widget:
                return

            # Clean up child widgets first
            for child in widget.findChildren(QWidget):
                if hasattr(child, 'cleanup') and hasattr(child, 'widget_id'):
                    try:
                        await child.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up child widget {child.widget_id}: {e}")

            # Clean up main widget
            if hasattr(widget, 'cleanup'):
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
            if not tag:
                return

            # Get subscribed widgets
            widget_ids = self._tag_subscriptions.get(tag, set())
            if not widget_ids:
                return

            # Update each subscribed widget
            for widget_id in widget_ids:
                widget_data = self._widgets.get(widget_id)
                if not widget_data:
                    continue

                widget = widget_data.get('widget_ref')
                if not widget or not hasattr(widget, 'update'):
                    continue

                await widget.update(data)

            # Publish UI update
            await self._message_broker.publish(f"ui/update/{tag}", {
                "value": data.get("value"),
                "timestamp": datetime.now().isoformat()
            })

            # Publish raw tag update
            await self._message_broker.publish(tag, {
                "value": data.get("value"),
                "timestamp": datetime.now().isoformat()
            })

            logger.debug(f"Processed tag update: {tag}={data.get('value')}")

        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            raise CoreError("Tag update failed", {
                "tag": tag,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle config updates."""
        try:
            # Forward config update to UI
            await self._message_broker.publish(
                "ui/update",
                {
                    "type": "config",
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
            )

            # Find widgets that need this config
            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if not widget:
                    continue

                # Check if widget wants this config update
                update_tags = getattr(widget, '_update_tags', [])
                if any(t.startswith("config.") for t in update_tags):
                    await widget.handle_ui_update({"config": data})

        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._message_broker.publish(
                "ui/error",
                {
                    "error": str(e),
                    "context": "config_update_handler",
                    "timestamp": datetime.now().isoformat()
                }
            )

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
            for widget_id in list(self._widgets.keys()):
                await self.unregister_widget(widget_id)

            self._is_initialized = False
            logger.debug("UI update manager shutdown complete")

        except Exception as e:
            logger.exception("Error during UI update manager shutdown")
            raise CoreError("Failed to shutdown UI update manager", {
                "error": str(e)
            })

    async def _handle_data_operation(self, tag: str, data: Dict[str, Any]) -> None:
        """Handle data operations through DataManager."""
        try:
            if tag.endswith("/list"):
                # Handle file listing through DataManager
                response = await self._message_broker.request(
                    "data/list_files",
                    {
                        "type": tag.split("/")[0],  # Extract type from tag
                        **data
                    },
                    timeout=2.0
                )
            else:
                # Handle other data operations (load/save/delete)
                response = await self._message_broker.request(
                    f"data/{tag}",
                    data,
                    timeout=2.0
                )

            if response and "error" in response:
                logger.error(f"Data operation failed: {response['error']}")
                return

            # Update UI based on operation type
            if tag.endswith("/list"):
                await self._handle_file_list_update(tag.split("/")[0], response.get("files", []))
            elif tag.endswith("/load"):
                await self._handle_file_load_update(tag.split("/")[0], response.get("value", {}))
            elif tag.endswith("/save"):
                await self._handle_file_save_update(tag.split("/")[0], data.get("name", ""))
            elif tag.endswith("/delete"):
                await self._handle_file_delete_update(tag.split("/")[0], data.get("name", ""))

        except Exception as e:
            logger.error(f"Error handling data operation: {e}")

    async def _handle_config_operation(self, tag: str, data: Dict[str, Any]) -> None:
        """Handle configuration operations through ConfigManager."""
        try:
            # Config operations go directly to ConfigManager
            if tag == "config/get":
                # Get config value
                response = await self._message_broker.request(
                    "config/get",
                    {
                        "config_type": data.get("config_type"),
                        "key": data.get("key")
                    },
                    timeout=2.0
                )
            else:
                # Other config operations
                response = await self._message_broker.request(
                    tag,
                    data,
                    timeout=2.0
                )

            if response and "error" in response:
                logger.error(f"Config operation failed: {response['error']}")
                return

            # Forward config update to UI
            await self._message_broker.publish(
                "ui/update",
                {
                    "type": "config",
                    "data": response,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error handling config operation: {e}")
            await self._message_broker.publish(
                "ui/error",
                {
                    "error": str(e),
                    "context": "config_operation",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_user_operation(self, tag: str, data: Dict[str, Any]) -> None:
        """Handle user operations."""
        try:
            # User operations go to UserManager
            response = await self._message_broker.request(
                tag,
                data,
                timeout=2.0
            )

            if response and "error" in response:
                logger.error(f"User operation failed: {response['error']}")
                return

            # Handle user update
            if response:
                await self._handle_user_update(tag, response)

        except Exception as e:
            logger.error(f"Error handling user operation: {e}")

    async def send_update(self, tag: str, data: Dict[str, Any]) -> None:
        """Send a UI update request."""
        try:
            # Route based on operation type
            if tag.startswith(("parameters/", "patterns/", "sequences/")):
                await self._handle_data_operation(tag, data)
            elif tag.startswith("config/"):
                await self._handle_config_operation(tag, data)
            elif tag.startswith("user/"):
                await self._handle_user_operation(tag, data)
            else:
                # Handle other UI updates
                await self._message_broker.publish(f"ui/update/{tag}", data)

        except Exception as e:
            logger.error(f"Error sending UI update: {e}")

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

            # Forward sequence loaded update to all subscribed widgets
            for widget_id in self._tag_subscriptions.get("sequence.loaded", set()):
                widget_data = self._widgets.get(widget_id)
                if not widget_data:
                    logger.warning(f"Widget {widget_id} not found in registered widgets")
                    continue

                widget = widget_data.get('widget_ref')
                if not widget:
                    logger.warning(f"Widget reference not found for {widget_id}")
                    continue

                logger.debug(f"Sending sequence.loaded update to widget {widget_id}")
                if hasattr(widget, 'handle_ui_update'):
                    try:
                        await widget.handle_ui_update({"sequence.loaded": data})
                        logger.debug(f"Successfully sent update to widget {widget_id}")
                    except Exception as e:
                        logger.error(f"Error sending update to widget {widget_id}: {e}")

            # Also send through general update mechanism
            await self.send_update(
                "sequence.loaded",
                data
            )

            logger.debug(f"Sequence loaded event handled: {data.get('name', 'unnamed')}")

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

    async def _handle_list_files_response(self, data: Dict[str, Any]) -> None:
        """Handle response to list files request."""
        try:
            file_type = data.get("type")
            files = data.get("files", [])

            if not file_type:
                raise ValueError("No file type in response")

            # Find widgets that requested this file type
            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if not widget or not hasattr(widget, "update_file_list"):
                    continue

                # Match widget type to file type
                if (
                    ("parameter_editor" in widget_id and file_type == "parameters") or
                    ("pattern_editor" in widget_id and file_type == "patterns") or
                    ("sequence_builder" in widget_id and file_type == "sequences")
                ):
                    await widget.update_file_list(files)
                    logger.debug(f"Updated {widget_id} with {len(files)} {file_type} files")

        except Exception as e:
            logger.error(f"Error handling list files response: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "list_files_response",
                "timestamp": datetime.now().isoformat()
            })
