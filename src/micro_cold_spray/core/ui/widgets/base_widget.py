"""Base widget class with standardized ID handling and cleanup."""
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import asyncio

from loguru import logger
from PySide6.QtWidgets import QWidget

from micro_cold_spray.core.exceptions import UIError

# Avoid circular import
if TYPE_CHECKING:
    from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager


class BaseWidget(QWidget):
    """Base widget class with common functionality."""

    def __init__(
        self,
        widget_id: str,
        ui_manager: 'UIUpdateManager',
        update_tags: List[str],
        parent: Optional[QWidget] = None
    ):
        """Initialize base widget.
        
        Args:
            widget_id: Unique widget identifier
            ui_manager: UI update manager instance
            update_tags: List of topics to receive updates for
            parent: Parent widget
        """
        super().__init__(parent)
        self._widget_id = widget_id
        self._ui_manager = ui_manager
        self._update_tags = update_tags
        self._init_task = None

        # Schedule async initialization
        self._init_task = asyncio.create_task(self.initialize())
        self._init_task.add_done_callback(self._on_init_complete)
        logger.debug(f"Created initialization task for widget {widget_id}")

    def _on_init_complete(self, task):
        """Handle completion of initialization task."""
        try:
            task.result()  # This will raise any exceptions that occurred
            logger.debug(f"Widget {self._widget_id} initialization completed successfully")
        except Exception as e:
            logger.error(f"Widget {self._widget_id} initialization failed: {e}")

    async def initialize(self) -> None:
        """Initialize widget and register with UI manager."""
        try:
            # Register with UI manager
            await self._ui_manager.register_widget(self._widget_id, self, self._update_tags)
            logger.debug(f"Initialized base widget {self._widget_id}")

            # Call widget-specific initialization
            await self._initialize()

        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "operation": "initialize",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error initializing widget: {error_context}")
            raise UIError("Failed to initialize widget", error_context) from e

    async def _initialize(self) -> None:
        """Widget-specific initialization. Override in derived classes."""
        pass

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI update from UIUpdateManager.
        
        Args:
            data: Update data dictionary
        """
        raise NotImplementedError("Subclasses must implement handle_ui_update")

    async def cleanup(self) -> None:
        """Clean up widget resources and unregister."""
        try:
            # Clean up child widgets first
            for child in self.findChildren(QWidget):
                if hasattr(child, 'cleanup') and hasattr(child, 'widget_id'):
                    try:
                        await child.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up child widget {child.widget_id}: {e}")

            # Clean up widget-specific resources
            try:
                await self._cleanup_resources()
            except Exception as e:
                logger.error(f"Error cleaning up widget resources: {e}")

            # Unregister from UI manager
            if hasattr(self, '_ui_manager') and self._ui_manager is not None:
                try:
                    await self._ui_manager.unregister_widget(self._widget_id)
                    logger.debug(f"Unregistered widget: {self._widget_id}")
                except Exception as e:
                    error_context = {
                        "widget_id": self._widget_id,
                        "operation": "unregister",
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.error(f"Error unregistering widget: {error_context}")
                    raise UIError("Failed to unregister widget", error_context) from e

        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "operation": "cleanup",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error during cleanup: {error_context}")
            # Don't re-raise - we want cleanup to continue even if there are errors

    @property
    def widget_id(self) -> str:
        """Get widget ID."""
        return self._widget_id

    async def _cleanup_resources(self) -> None:
        """Clean up widget-specific resources. Override in derived classes."""
        pass

    async def send_update(self, topic: str, data: Dict[str, Any]) -> None:
        """Send an update through the UI manager.
        
        Args:
            topic: Update topic
            data: Update data
        """
        try:
            await self._ui_manager.send_update(topic, data)
            logger.debug(f"Widget {self._widget_id} sent update: {topic}={data}")
        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "topic": topic,
                "data": data,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error sending update: {error_context}")
            raise UIError("Failed to send update", error_context) from e

    @property
    def config_manager(self):
        """Get the config manager instance."""
        return self._ui_manager._config_manager
