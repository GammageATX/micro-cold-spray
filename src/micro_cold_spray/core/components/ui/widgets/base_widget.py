"""Base widget class with standardized ID handling and cleanup."""
from typing import Optional, List, Dict, Any
import logging
from PySide6.QtWidgets import QWidget
import asyncio

from ..managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

class BaseWidget(QWidget):
    """Base class for all custom widgets with standardized ID handling.
    
    Provides:
    - Standardized widget ID validation and management
    - Consistent cleanup pattern
    - UI update manager integration
    - Basic error handling
    """
    
    # Valid widget type prefixes
    VALID_TYPES = {'widget', 'tab', 'control', 'display', 'monitor'}
    
    # Valid location identifiers
    VALID_LOCATIONS = {'main', 'dashboard', 'motion', 'editor', 'system'}
    
    async def initialize(self) -> None:
        """Async initialization."""
        try:
            # Register with UI manager
            await self._ui_manager.register_widget(
                widget_id=self._widget_id,
                update_tags=self._update_tags,
                widget=self  # Pass widget instance for registry
            )
            logger.debug(f"Registered {self._widget_id} for tags: {self._update_tags}")
        except Exception as e:
            logger.error(f"Error registering {self._widget_id}: {e}")
            raise
    
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
    
    @property
    def widget_id(self) -> str:
        """Get widget ID."""
        return self._widget_id
    
    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI update from UIUpdateManager.
        
        Args:
            data: Dictionary of tag updates
            
        Note: Override in derived classes to handle specific updates
        """
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
                    logger.error(f"Error unregistering {self._widget_id}: {e}")
            
            # Call parent cleanup if exists and is a BaseWidget
            parent = self.parent()
            if parent is not None and isinstance(parent, BaseWidget):
                try:
                    await parent.cleanup()
                except Exception as e:
                    logger.error(f"Error in parent cleanup for {self._widget_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error during cleanup of {self._widget_id}: {e}")
            # Don't re-raise - we want cleanup to continue
    
    async def send_update(self, tag: str, value: Any) -> None:
        """Send a tag update through the UI manager.
        
        Args:
            tag: Tag name to update
            value: New tag value
        """
        try:
            await self._ui_manager.send_update(tag, value)
            logger.debug(f"Widget {self._widget_id} sent update: {tag}={value}")
        except Exception as e:
            logger.error(f"Error sending update from {self._widget_id}: {e}")
            # Re-raise since this is a user action that should be handled
            raise