"""UI Update Manager for coordinating widget updates."""
import logging
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from ..widgets.base_widget import BaseWidget

logger = logging.getLogger(__name__)


class UIUpdateManager:
    """Manager for distributing tag updates to widgets."""

    def __init__(self):
        """Initialize UI update manager."""
        self._widgets: Dict[str, Dict[str, Any]] = {}  # widget_id -> {widget, tags}
        self._tag_subscriptions: Dict[str, Set[str]] = {}  # tag -> set of widget_ids
        logger.info("UI update manager initialized")

    async def register_widget(self, widget_id: str, widget: 'BaseWidget', update_tags: List[str]) -> None:
        """Register a widget for updates.
        
        Args:
            widget_id: Unique widget identifier
            widget: Widget instance
            update_tags: List of tags to receive updates for
        """
        try:
            # Store widget reference and its tags
            self._widgets[widget_id] = {
                'widget': widget,
                'tags': set(update_tags)
            }

            # Update tag subscriptions
            for tag in update_tags:
                if tag not in self._tag_subscriptions:
                    self._tag_subscriptions[tag] = set()
                self._tag_subscriptions[tag].add(widget_id)

            logger.debug(f"Registered widget {widget_id} with tags {update_tags}")

        except Exception as e:
            logger.error(f"Failed to register widget {widget_id}: {e}")
            raise

    async def unregister_widget(self, widget_id: str) -> None:
        """Unregister a widget.
        
        Args:
            widget_id: Widget identifier to unregister
        """
        try:
            if widget_id not in self._widgets:
                return

            # Remove from tag subscriptions
            widget_data = self._widgets[widget_id]
            for tag in widget_data['tags']:
                if tag in self._tag_subscriptions:
                    self._tag_subscriptions[tag].discard(widget_id)
                    if not self._tag_subscriptions[tag]:
                        del self._tag_subscriptions[tag]

            # Remove widget
            del self._widgets[widget_id]
            logger.debug(f"Unregistered widget {widget_id}")

        except Exception as e:
            logger.error(f"Failed to unregister widget {widget_id}: {e}")
            raise

    async def handle_tag_update(self, tag: str, value: Any) -> None:
        """Distribute a tag update to subscribed widgets.
        
        Args:
            tag: Tag that was updated
            value: New tag value
        """
        try:
            # Find widgets subscribed to this tag
            widget_ids = self._tag_subscriptions.get(tag, set())
            
            # Send update to each subscribed widget
            for widget_id in widget_ids:
                widget_data = self._widgets.get(widget_id)
                if not widget_data:
                    continue
                    
                widget = widget_data['widget']
                if not hasattr(widget, 'handle_tag_update'):
                    continue

                try:
                    await widget.handle_tag_update(tag, value)
                except Exception as e:
                    logger.error(f"Error sending tag update to widget {widget_id}: {e}")

        except Exception as e:
            logger.error(f"Error handling tag update for {tag}: {e}")

    def get_widget(self, widget_id: str) -> Optional['BaseWidget']:
        """Get a widget by ID.
        
        Args:
            widget_id: Widget identifier
            
        Returns:
            Widget instance if found, None otherwise
        """
        widget_data = self._widgets.get(widget_id)
        return widget_data['widget'] if widget_data else None
