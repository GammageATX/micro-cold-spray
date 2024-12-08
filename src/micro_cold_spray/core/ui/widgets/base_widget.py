"""Base widget class with standardized ID handling and cleanup."""
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from loguru import logger
from PySide6.QtWidgets import QWidget

from micro_cold_spray.core.exceptions import UIError, ValidationError

# Avoid circular import
if TYPE_CHECKING:
    from micro_cold_spray.core.ui.managers.ui_update_manager import UIUpdateManager


class BaseWidget(QWidget):
    """Base class for all custom widgets with standardized ID handling."""

    def __init__(
        self,
        widget_id: str,
        ui_manager: 'UIUpdateManager',
        update_tags: Optional[List[str]] = None,
        parent: Optional[QWidget] = None
    ):
        """Initialize base widget."""
        super().__init__(parent)
        self._widget_id = widget_id
        self._ui_manager = ui_manager
        self._update_tags = update_tags or []
        self._init_task = None

        # Schedule async initialization
        self._init_task = asyncio.create_task(self.initialize())
        self._init_task.add_done_callback(self._on_init_complete)
        logger.info(f"Created initialization task for widget {widget_id}")

    def _on_init_complete(self, task):
        """Handle completion of initialization task."""
        try:
            task.result()  # This will raise any exceptions that occurred
            logger.info(f"Widget {self._widget_id} initialization completed successfully")
        except Exception as e:
            logger.error(f"Widget {self._widget_id} initialization failed: {e}")
            logger.exception("Initialization error details:")

    async def initialize(self) -> None:
        """Async initialization."""
        try:
            logger.info(f"Starting initialization for widget {self._widget_id}")
            # Register with UI manager
            error_context = {
                'widget_id': self._widget_id,
                'update_tags': self._update_tags,
                'timestamp': datetime.now().isoformat()
            }

            try:
                await self._ui_manager.register_widget(
                    self._widget_id,
                    self._update_tags,
                    self
                )
                logger.info(f"Widget {self._widget_id} registered with UI manager")
            except Exception as e:
                raise UIError("Failed to register widget", error_context) from e

        except ValidationError as e:
            logger.error(f"Widget validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Error registering widget: {error_context}")
            raise UIError("Widget initialization failed", error_context) from e

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager.

        This is the base implementation that should be overridden by widgets
        that need to handle specific updates.

        Args:
            data: Dictionary containing update data
        """
        logger.debug(f"Base widget {self._widget_id} received update: {data}")
        # Base implementation does nothing
        pass

    @property
    def widget_id(self) -> str:
        """Get widget ID."""
        return self._widget_id

    async def _cleanup_resources(self) -> None:
        """Clean up widget-specific resources. Override in derived classes."""
        pass

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

        except Exception:
            error_context = {
                "widget_id": self._widget_id,
                "operation": "cleanup",
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error during cleanup: {error_context}")
            # Don't re-raise - we want cleanup to continue

    async def send_update(self, tag: str, value: Any) -> None:
        """Send a tag update through the UI manager."""
        try:
            await self._ui_manager.send_update(tag, value)
            logger.debug(
                f"Widget {
                    self._widget_id} sent update: {tag}={value}")
        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "tag": tag,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error sending update: {error_context}")
            raise UIError("Failed to send update", error_context) from e

    @property
    def config_manager(self):
        """Get the config manager instance."""
        return self._ui_manager._config_manager
