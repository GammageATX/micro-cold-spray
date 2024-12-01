"""Base widget class with standardized ID handling and cleanup."""
from typing import Optional, List, Dict, Any
from loguru import logger
from PySide6.QtWidgets import QWidget
import asyncio
from datetime import datetime

from ..managers.ui_update_manager import UIUpdateManager
from ....exceptions import UIError, ValidationError

class BaseWidget(QWidget):
    """Base class for all custom widgets with standardized ID handling."""
    
    # Valid widget type prefixes
    VALID_TYPES = {'widget', 'tab', 'control', 'display', 'monitor'}
    
    # Valid location identifiers
    VALID_LOCATIONS = {'dashboard', 'system', 'main', 'motion', 'editor'}
    
    def __init__(
        self,
        widget_id: str,
        ui_manager: UIUpdateManager,
        update_tags: Optional[List[str]] = None,
        parent: Optional[QWidget] = None
    ):
        """Initialize base widget."""
        super().__init__(parent)
        self._widget_id = widget_id
        self._ui_manager = ui_manager
        self._update_tags = update_tags or []
        
        # Schedule async initialization
        asyncio.create_task(self.initialize())
    
    async def initialize(self) -> None:
        """Async initialization."""
        try:
            # Validate widget ID format
            parts = self._widget_id.split('_')
            if len(parts) < 2:
                raise ValidationError("Invalid widget ID format - must be type_location_name")
            
            widget_type, location = parts[0], parts[1]
            
            if widget_type not in self.VALID_TYPES:
                raise ValidationError(f"Invalid widget type: {widget_type}. Must be one of: {self.VALID_TYPES}")
                
            if location not in self.VALID_LOCATIONS:
                raise ValidationError(f"Invalid widget location: {location}. Must be one of: {self.VALID_LOCATIONS}")
            
            # Register with UI manager if validation passes
            await self._ui_manager.register_widget(
                widget_id=self._widget_id,
                update_tags=self._update_tags,
                widget=self
            )
            logger.debug(f"Registered {self._widget_id} for tags: {self._update_tags}")
            
        except ValidationError as e:
            logger.warning(f"Widget validation failed: {e}")
            self.setEnabled(False)  # Disable invalid widgets
            
        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "update_tags": self._update_tags,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error registering widget: {error_context}")
            raise UIError("Failed to register widget", error_context) from e
    
    @property
    def widget_id(self) -> str:
        """Get widget ID."""
        return self._widget_id
    
    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI update from UIUpdateManager."""
        logger.warning(
            f"Base handle_ui_update called for {self._widget_id}. "
            "Override in derived class."
        )
    
    async def cleanup(self) -> None:
        """Clean up widget resources."""
        try:
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
            
            # Call parent cleanup if exists and is a BaseWidget
            parent = self.parent()
            if parent is not None and isinstance(parent, BaseWidget):
                try:
                    await parent.cleanup()
                except Exception as e:
                    error_context = {
                        "widget_id": self._widget_id,
                        "parent_id": parent.widget_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    logger.error(f"Error in parent cleanup: {error_context}")
                    raise UIError("Parent cleanup failed", error_context) from e
                
        except Exception as e:
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
            logger.debug(f"Widget {self._widget_id} sent update: {tag}={value}")
        except Exception as e:
            error_context = {
                "widget_id": self._widget_id,
                "tag": tag,
                "value": value,
                "timestamp": datetime.now().isoformat()
            }
            logger.error(f"Error sending update: {error_context}")
            raise UIError("Failed to send update", error_context) from e