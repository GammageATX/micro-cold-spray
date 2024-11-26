"""Pattern management component."""
from typing import Dict, Any, Optional
import logging
import time

from ....infrastructure.messaging.message_broker import MessageBroker, Message, MessageType
from ....infrastructure.tags.tag_manager import TagManager
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator

logger = logging.getLogger(__name__)

class PatternManager:
    """Manages spray patterns and pattern configurations."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        tag_manager: TagManager,
        process_validator: ProcessValidator
    ):
        self._config = config_manager
        self._tag_manager = tag_manager
        self._validator = process_validator
        self._message_broker = MessageBroker()
        
        # Only subscribe to pattern-related messages
        self._message_broker.subscribe("pattern_update", self._handle_pattern_update)
        
        logger.info("Pattern manager initialized")

    async def get_pattern(self, pattern_name: str) -> Dict[str, Any]:
        """Get a pattern by name."""
        try:
            if pattern_name not in self._patterns:
                raise KeyError(f"Pattern not found: {pattern_name}")
                
            # Update pattern access tag
            self._tag_manager.set_tag(
                "patterns.access",
                {
                    "pattern_name": pattern_name,
                    "action": "read",
                    "timestamp": time.time()
                }
            )
            
            # Publish pattern access event
            self._message_broker.publish(
                Message(
                    topic="patterns/accessed",
                    type=MessageType.PROCESS_UPDATE,
                    data={"pattern_name": pattern_name}
                )
            )
            
            return self._patterns[pattern_name].copy()
            
        except Exception as e:
            logger.error(f"Error getting pattern {pattern_name}: {e}")
            self._message_broker.publish(
                Message(
                    topic="patterns/error",
                    type=MessageType.ERROR,
                    data={"error": str(e), "pattern_name": pattern_name}
                )
            )
            raise

    async def update_pattern(self, pattern_name: str, updates: Dict[str, Any]) -> None:
        """Update a pattern configuration."""
        try:
            if pattern_name not in self._patterns:
                raise KeyError(f"Pattern not found: {pattern_name}")
                
            # Validate pattern updates
            await self._validator.validate_pattern(
                self._patterns[pattern_name]['type'],
                updates
            )
            
            # Update pattern
            self._patterns[pattern_name].update(updates)
            
            # Update through config manager to persist changes
            self._config.update_config(
                'operation',
                {'patterns': {pattern_name: self._patterns[pattern_name]}}
            )
            
            # Update pattern change tag
            self._tag_manager.set_tag(
                "patterns.change",
                {
                    "pattern_name": pattern_name,
                    "updates": updates,
                    "timestamp": time.time()
                }
            )
            
            # Publish pattern update event
            self._message_broker.publish(
                Message(
                    topic="patterns/updated",
                    type=MessageType.PROCESS_UPDATE,
                    data={
                        "pattern_name": pattern_name,
                        "updates": updates
                    }
                )
            )
            
        except Exception as e:
            logger.error(f"Error updating pattern {pattern_name}: {e}")
            self._message_broker.publish(
                Message(
                    topic="patterns/error",
                    type=MessageType.ERROR,
                    data={
                        "error": str(e),
                        "pattern_name": pattern_name,
                        "updates": updates
                    }
                )
            )
            raise

    async def create_pattern(self, pattern_name: str, pattern_data: Dict[str, Any]) -> None:
        """Create a new pattern."""
        try:
            if pattern_name in self._patterns:
                raise ValueError(f"Pattern already exists: {pattern_name}")
                
            # Validate new pattern
            await self._validator.validate_pattern(
                pattern_data['type'],
                pattern_data['parameters']
            )
            
            # Add new pattern
            self._patterns[pattern_name] = pattern_data
            
            # Update through config manager to persist
            self._config.update_config(
                'operation',
                {'patterns': {pattern_name: pattern_data}}
            )
            
            # Update pattern creation tag
            self._tag_manager.set_tag(
                "patterns.creation",
                {
                    "pattern_name": pattern_name,
                    "pattern": pattern_data,
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating pattern {pattern_name}: {e}")
            raise

    def delete_pattern(self, pattern_name: str) -> None:
        """Delete a pattern."""
        try:
            if pattern_name not in self._patterns:
                raise KeyError(f"Pattern not found: {pattern_name}")
                
            # Remove pattern
            del self._patterns[pattern_name]
            
            # Update through config manager to persist
            self._config.update_config(
                'operation',
                {'patterns': self._patterns}
            )
            
            # Update pattern deletion tag
            self._tag_manager.set_tag(
                "patterns.deletion",
                {
                    "pattern_name": pattern_name,
                    "timestamp": time.time()
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting pattern {pattern_name}: {e}")
            raise

    def list_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get all patterns."""
        return self._patterns.copy()