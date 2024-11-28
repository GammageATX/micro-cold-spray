"""Pattern management component."""
from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime
from pathlib import Path

from ....infrastructure.messaging.message_broker import MessageBroker
from ....config.config_manager import ConfigManager
from ....components.process.validation.process_validator import ProcessValidator
from ....exceptions import OperationError

class PatternManager:
    """Manages spray patterns and pattern configurations."""
    
    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager,
        process_validator: ProcessValidator
    ):
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._validator = process_validator
        self._patterns: Dict[str, Dict[str, Any]] = {}
        self._is_initialized = False
        logger.info("Pattern manager initialized")

    async def initialize(self) -> None:
        """Initialize pattern manager."""
        try:
            if self._is_initialized:
                return
                
            # Load patterns from config
            patterns_config = self._config_manager.get_config('patterns')
            self._patterns = patterns_config.get('patterns', {})
            
            # Subscribe to pattern-related messages
            await self._message_broker.subscribe(
                "pattern/create",
                self._handle_pattern_create
            )
            await self._message_broker.subscribe(
                "pattern/update",
                self._handle_pattern_update
            )
            await self._message_broker.subscribe(
                "pattern/delete",
                self._handle_pattern_delete
            )
            
            self._is_initialized = True
            logger.info("Pattern manager initialization complete")
            
        except Exception as e:
            logger.error(f"Failed to initialize pattern manager: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "pattern/init",
                "timestamp": datetime.now().isoformat()
            })
            raise OperationError(f"Pattern manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown pattern manager."""
        try:
            # Save patterns to config if needed
            await self._config_manager.update_config('patterns', {'patterns': self._patterns})
            self._is_initialized = False
            logger.info("Pattern manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during pattern manager shutdown")
            raise OperationError(f"Pattern manager shutdown failed: {str(e)}") from e

    async def _handle_pattern_update(self, data: Dict[str, Any]) -> None:
        """Handle pattern update messages."""
        try:
            pattern_name = data.get('pattern_name')
            updates = data.get('updates')
            
            if not pattern_name or not updates:
                raise ValueError("Invalid pattern update message")
                
            await self.update_pattern(pattern_name, updates)
            
        except Exception as e:
            logger.error(f"Error handling pattern update: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def get_pattern(self, pattern_name: str) -> Dict[str, Any]:
        """Get a pattern by name."""
        try:
            if pattern_name not in self._patterns:
                raise KeyError(f"Pattern not found: {pattern_name}")
                
            # Publish pattern access event
            await self._message_broker.publish(
                "patterns/accessed",
                {
                    "pattern_name": pattern_name,
                    "action": "read",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return self._patterns[pattern_name].copy()
            
        except Exception as e:
            logger.error(f"Error getting pattern {pattern_name}: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "pattern_name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to get pattern: {str(e)}") from e

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
            await self._config_manager.update_config(
                'patterns',
                {'patterns': {pattern_name: self._patterns[pattern_name]}}
            )
            
            # Publish pattern update event
            await self._message_broker.publish(
                "patterns/updated",
                {
                    "pattern_name": pattern_name,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating pattern {pattern_name}: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "pattern_name": pattern_name,
                    "updates": updates,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to update pattern: {str(e)}") from e

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
            await self._config_manager.update_config(
                'patterns',
                {'patterns': {pattern_name: pattern_data}}
            )
            
            # Update pattern creation tag
            await self._tag_manager.set_tag(
                "patterns.creation",
                {
                    "pattern_name": pattern_name,
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Publish pattern creation event
            await self._message_broker.publish(
                "patterns/created",
                {
                    "pattern_name": pattern_name,
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating pattern {pattern_name}: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "pattern_name": pattern_name,
                    "pattern": pattern_data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to create pattern: {str(e)}") from e

    async def delete_pattern(self, pattern_name: str) -> None:
        """Delete a pattern."""
        try:
            if pattern_name not in self._patterns:
                raise KeyError(f"Pattern not found: {pattern_name}")
                
            # Remove pattern
            del self._patterns[pattern_name]
            
            # Update through config manager to persist
            await self._config_manager.update_config(
                'patterns',
                {'patterns': self._patterns}
            )
            
            # Update pattern deletion tag
            await self._tag_manager.set_tag(
                "patterns.deletion",
                {
                    "pattern_name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Publish pattern deletion event
            await self._message_broker.publish(
                "patterns/deleted",
                {
                    "pattern_name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting pattern {pattern_name}: {e}")
            await self._message_broker.publish(
                "patterns/error",
                {
                    "error": str(e),
                    "pattern_name": pattern_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to delete pattern: {str(e)}") from e

    def list_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Get all patterns."""
        return self._patterns.copy()

    async def _handle_pattern_create(self, data: Dict[str, Any]) -> None:
        """Handle pattern creation requests."""
        try:
            pattern_name = data.get("name")
            pattern_data = data.get("pattern")
            
            if not pattern_name or not pattern_data:
                raise OperationError("Missing pattern name or data")
            
            # Validate pattern parameters
            validation_result = await self._validator.validate_parameters(pattern_data.get("parameters", {}))
            if not validation_result["valid"]:
                await self._message_broker.publish("error", {
                    "error": "Invalid pattern parameters",
                    "context": validation_result["errors"],
                    "topic": "pattern/create",
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            # Store pattern
            self._patterns[pattern_name] = pattern_data
            
            # Publish success
            await self._message_broker.publish(
                "pattern/create/response",
                {
                    "name": pattern_name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating pattern: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "pattern_create",
                "topic": "pattern/create",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_pattern_update(self, data: Dict[str, Any]) -> None:
        """Handle pattern update requests."""
        try:
            pattern_name = data.get("name")
            pattern_data = data.get("pattern")
            
            if not pattern_name or not pattern_data:
                raise OperationError("Missing pattern name or data")
            
            if pattern_name not in self._patterns:
                raise OperationError(f"Pattern not found: {pattern_name}")
            
            # Validate updated parameters
            validation_result = await self._validator.validate_parameters(pattern_data.get("parameters", {}))
            if not validation_result["valid"]:
                await self._message_broker.publish("error", {
                    "error": "Invalid pattern parameters",
                    "context": validation_result["errors"],
                    "topic": "pattern/update",
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            # Update pattern
            self._patterns[pattern_name].update(pattern_data)
            
            # Publish success
            await self._message_broker.publish(
                "pattern/update/response",
                {
                    "name": pattern_name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error updating pattern: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "pattern_update",
                "topic": "pattern/update",
                "timestamp": datetime.now().isoformat()
            })

    async def _handle_pattern_delete(self, data: Dict[str, Any]) -> None:
        """Handle pattern deletion requests."""
        try:
            pattern_name = data.get("name")
            
            if not pattern_name:
                raise OperationError("Missing pattern name")
            
            if pattern_name not in self._patterns:
                raise OperationError(f"Pattern not found: {pattern_name}")
            
            # Delete pattern
            del self._patterns[pattern_name]
            
            # Publish success
            await self._message_broker.publish(
                "pattern/delete/response",
                {
                    "name": pattern_name,
                    "success": True,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error deleting pattern: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "context": "pattern_delete",
                "topic": "pattern/delete",
                "timestamp": datetime.now().isoformat()
            })