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
from ...process.data.data_manager import DataManager
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
        config_manager: ConfigManager,
        data_manager: DataManager
    ) -> None:
        """Initialize UI update manager."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._data_manager = data_manager
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
            await self._message_broker.subscribe("config/response", self._handle_config_response)
            await self._message_broker.subscribe("data/files/listed", self._handle_data_files_listed)
            await self._message_broker.subscribe("tag/update", self._handle_tag_update)
            await self._message_broker.subscribe("config/update", self._handle_config_update)
            await self._message_broker.subscribe("sequence/loaded", self._handle_sequence_loaded)
            await self._message_broker.subscribe("sequence/state", self._handle_sequence_state)

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

            logger.info(f"UI manager handling update type: {update_type} with data: {update_data}")

            # Special handling for data list updates
            if update_type == "data.list":
                # Find widgets that need this update
                for widget_id, widget_data in self._widgets.items():
                    widget = widget_data.get('widget_ref')
                    if widget and hasattr(widget, "handle_ui_update"):
                        logger.info(f"Forwarding data.list update to widget {widget_id}")
                        await widget.handle_ui_update({update_type: update_data})
            else:
                # Find widgets that need this update
                for widget_id, widget_data in self._widgets.items():
                    widget = widget_data.get('widget_ref')
                    if widget and hasattr(widget, "handle_ui_update"):
                        await widget.handle_ui_update(update_data)

            logger.debug(f"Processed UI update: {update_type}")

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "ui_update_handler",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_ui_error(self, error_msg: Dict[str, Any]) -> None:
        """Handle UI-related errors from the message broker."""
        try:
            operation = error_msg.get("operation", "unknown")
            error = error_msg.get("error", "Unknown error")

            # Just log the error - don't try to publish it again
            logger.error(f"UI error in {operation}: {error}")

        except Exception as e:
            # Just log any errors in the error handler
            logger.critical(f"Error in UI error handler: {str(e)}")

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

    async def send_update(self, operation: str, data: Dict[str, Any]) -> None:
        """Send an update to the message broker."""
        try:
            logger.info(f"UI Manager sending update: {operation} with data: {data}")

            if operation == "data/list":
                # Request file list from DataManager
                logger.info("Forwarding file list request to DataManager")
                await self._message_broker.publish("data/list_files", {
                    "type": data.get("type")
                })
                logger.info(f"Sent file list request for type: {data.get('type')}")
                return

            if operation == "system/users":
                # Handle user list operations
                action = data.get("action")
                if action == "list":
                    # Request current user list
                    await self._message_broker.publish("config/get", {
                        "config_type": "application",
                        "key": "environment.user_history"
                    })
                elif action == "add":
                    # Get current config
                    app_config = await self._config_manager.get_config("application")
                    env_config = app_config.get("application", {}).get("environment", {})
                    current_users = list(env_config.get("user_history", []))

                    # Add new user if not already in list
                    new_user = data.get("user")
                    if new_user and new_user not in current_users:
                        current_users.append(new_user)

                        # Update just the environment section
                        await self._config_manager.update_config("application", {
                            "application": {
                                "environment": {
                                    "user": new_user,
                                    "user_history": current_users
                                }
                            }
                        })
                return

            if operation.startswith("config/get"):
                # Handle config get operations
                config_type = data.get("config_type")
                if not config_type:
                    raise ValueError("No config type specified for config get operation")

                await self._message_broker.publish("config/get", {
                    "config_type": config_type,
                    "key": data.get("key")
                })
                return

            if operation.startswith("data/"):
                # Handle other data operations
                await self._handle_data_operation(operation, data)
                return

            if operation.startswith("config/"):
                # Handle other config operations
                await self._handle_config_operation(operation, data)
                return

            # Default to UI update
            await self._message_broker.publish("ui/update", {
                "type": operation,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

        except Exception as e:
            logger.error(f"Error sending update: {str(e)}")
            # Raise UIError instead of trying to handle it here
            raise UIError(str(e), {
                "operation": "send_update",
                "error": str(e)
            })

    async def send_widget_update(self, widget_id: str, update_type: str, data: dict) -> None:
        """Send an update to a specific widget."""
        try:
            # Add logging to help debug the issue
            logger.debug(f"Sending update to widget {widget_id}, type: {update_type}, data: {data}")

            # Validate inputs
            if not widget_id or not update_type:
                raise ValueError("Widget ID and update type must be specified")

            # Get widget config
            widget_config = await self._config_manager.get_config("application")
            widgets = widget_config.get("window", {}).get("widgets", {})
            if not widgets:
                logger.warning("No widget configuration found")
                return

            # Validate widget exists in registry
            if widget_id not in self._widgets:
                logger.warning(f"Widget {widget_id} not found in registry")
                return

            # Send the update
            widget_data = self._widgets[widget_id]
            widget = widget_data.get('widget_ref')
            if widget and hasattr(widget, 'handle_update'):
                await widget.handle_update(update_type, data)
            else:
                logger.warning(f"Widget {widget_id} cannot handle updates")

        except Exception as e:
            logger.error(f"Error sending widget update: {str(e)}")
            await self._handle_ui_error("send_widget_update", str(e))

    async def _handle_config_operation(self, operation: str, data: Dict[str, Any]) -> None:
        """Handle config operations."""
        try:
            if operation == "get_format":
                # Get format from file_format.yaml
                format_type = data.get("type")
                config = await self._config_manager.get_config("file_format")
                format_data = config.get(format_type, {})
                await self._message_broker.publish("ui/update", {
                    "type": "config.format",
                    "format": format_data
                })
            elif operation == "request":
                # Get config from ConfigManager
                config_type = data.get("type")
                config_data = await self._config_manager.get_config(config_type)
                await self._message_broker.publish("ui/update", {
                    "type": "config.update",
                    "data": config_data
                })
        except Exception as e:
            logger.error(f"Error handling config operation: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "config_operation",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_data_operation(self, operation: str, data: Dict[str, Any]) -> None:
        """Handle data operations."""
        try:
            logger.debug(f"Handling data operation: {operation} with data: {data}")

            if operation == "data/list":
                # Request file list from DataManager
                logger.debug(f"Requesting file list for type: {data.get('type')}")
                await self._message_broker.publish("data/list_files", {
                    "type": data.get("type")
                })
                return

            if operation == "data/load":
                # Load file through DataManager
                await self._message_broker.publish("data/load", {
                    "type": data.get("type"),
                    "name": data.get("name")
                })
                return

            if operation == "data/save":
                # Save file through DataManager
                await self._message_broker.publish("data/save", {
                    "type": data.get("type"),
                    "name": data.get("name"),
                    "value": data.get("value")
                })
                return

            if operation == "data/delete":
                # Delete file through DataManager
                await self._message_broker.publish("data/delete", {
                    "type": data.get("type"),
                    "name": data.get("name")
                })
                return

            if operation == "data/request":
                # Request data from DataManager
                await self._message_broker.publish("data/request", {
                    "type": data.get("type"),
                    "name": data.get("name")
                })
                return

            logger.warning(f"Unknown data operation: {operation}")

        except Exception as e:
            logger.error(f"Error handling data operation: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "data_operation_handler",
                "operation": operation,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_user_operation(self, operation: str, data: Dict[str, Any]) -> None:
        """Handle user operations."""
        try:
            if operation == "current":
                # Get current user from application config
                config = await self._config_manager.get_config("application")
                user = config.get("environment", {}).get("user", "")
                await self._message_broker.publish("ui/update", {
                    "type": "user.current",
                    "value": user
                })
        except Exception as e:
            logger.error(f"Error handling user operation: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "user_operation",
                "timestamp": datetime.now().isoformat()
            })

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

            # Send data.{type} update for all widgets
            update_data = {
                f"data.{file_type}": {
                    "files": files
                }
            }

            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if widget and hasattr(widget, "handle_ui_update"):
                    await widget.handle_ui_update(update_data)

            logger.debug(f"Updated widgets with {len(files)} {file_type} files")

        except Exception as e:
            logger.error(f"Error handling list files response: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "list_files_response",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_config_response(self, data: Dict[str, Any]) -> None:
        """Handle configuration response messages."""
        try:
            config_type = data.get("config_type")
            value = data.get("value")

            if not config_type or value is None:
                raise ValueError("Invalid config response - missing required fields")

            # Notify widgets of config update
            update_data = {
                f"config.{config_type}": value
            }

            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if widget and hasattr(widget, "handle_ui_update"):
                    await widget.handle_ui_update(update_data)

            logger.debug(f"Processed config response for {config_type}")

        except Exception as e:
            logger.error(f"Error handling config response: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "config_response_handler",
                "data": data,
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_data_files_listed(self, data: Dict[str, Any]) -> None:
        """Handle data files listed response."""
        try:
            # Forward to all widgets
            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if widget and hasattr(widget, "handle_ui_update"):
                    await widget.handle_ui_update({"data.list": data})
                else:
                    logger.warning(f"Widget {widget_id} does not have handle_ui_update method")

        except Exception as e:
            logger.error(f"Error handling data files listed: {e}")
            await self._message_broker.publish("ui/error", {
                "error": str(e),
                "context": "data_files_listed",
                "timestamp": datetime.now().isoformat()
            })
