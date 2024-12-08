"""UI update manager component."""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Set, Tuple

from loguru import logger

from micro_cold_spray.core.exceptions import UIError
from micro_cold_spray.core.infrastructure.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.process.data.data_manager import DataManager
from micro_cold_spray.core.ui.widgets.base_widget import BaseWidget


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
        self._pending_requests: Dict[str, Tuple[str, str]] = {}  # request_id -> (widget_id, tag)
        self._request_counter = 0

        logger.debug("UI update manager initialized")

    async def initialize(self) -> None:
        """Initialize the UI update manager."""
        try:
            # Subscribe to required topics
            await self._message_broker.subscribe("tag/response", self._handle_tag_response)
            await self._message_broker.subscribe("error", self._handle_error)
            await self._message_broker.subscribe("state/change", self._handle_state_change)
            await self._message_broker.subscribe("ui/response", self._handle_ui_response)

            self._is_initialized = True
            logger.info("UI update manager initialized")

        except Exception as e:
            logger.error(f"Failed to initialize UI update manager: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "ui_manager",
                    "error": str(e),
                    "context": "initialization",
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise UIError("Failed to initialize UI update manager") from e

    async def _handle_ui_response(self, data: Dict[str, Any]) -> None:
        """Handle UI response messages."""
        try:
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            widget_id, _ = self._pending_requests.pop(request_id)
            widget_data = self._widgets.get(widget_id)
            if not widget_data:
                return

            widget = widget_data.get('widget_ref')
            if not widget or not hasattr(widget, 'handle_ui_update'):
                return

            await widget.handle_ui_update(data)

        except Exception as e:
            logger.error(f"Error handling UI response: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "ui_manager",
                    "error": str(e),
                    "context": "ui_response",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _handle_state_change(self, data: Dict[str, Any]) -> None:
        """Handle state change messages."""
        try:
            state_type = data.get("type")
            state = data.get("state")
            if not state_type or not state:
                return

            # Update all widgets that care about this state
            for widget_id, widget_data in self._widgets.items():
                widget = widget_data.get('widget_ref')
                if not widget or not hasattr(widget, 'handle_ui_update'):
                    continue

                if f"{state_type}.state" in widget_data.get('tags', []):
                    await widget.handle_ui_update({f"{state_type}.state": state})

        except Exception as e:
            logger.error(f"Error handling state change: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "ui_manager",
                    "error": str(e),
                    "context": "state_change",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def send_ui_request(self, widget_id: str, request_type: str, data: Dict[str, Any]) -> None:
        """Send a UI request."""
        try:
            request_id = self._generate_request_id(widget_id)
            self._pending_requests[request_id] = (widget_id, request_type)

            await self._message_broker.publish(
                "ui/request",
                {
                    "request_id": request_id,
                    "type": request_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error sending UI request: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "ui_manager",
                    "error": str(e),
                    "context": "ui_request",
                    "widget_id": widget_id,
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def update_ui_state(self, state_type: str, state: Dict[str, Any]) -> None:
        """Update UI state."""
        try:
            await self._message_broker.publish(
                "ui/state",
                {
                    "type": state_type,
                    "state": state,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            logger.error(f"Error updating UI state: {e}")
            await self._message_broker.publish(
                "error",
                {
                    "source": "ui_manager",
                    "error": str(e),
                    "context": "ui_state",
                    "timestamp": datetime.now().isoformat()
                }
            )

    # ... rest of the file unchanged ...
