# src/micro_cold_spray/core/config/managers/config_manager.py
from typing import Dict, Any, Optional
import logging
from pathlib import Path
import yaml
from datetime import datetime
import asyncio

from ..infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)

class ConfigManager:
    """Manages application configuration."""
    
    def __init__(self, message_broker: Optional[MessageBroker] = None):
        """Initialize config manager.
        
        Args:
            message_broker: Optional message broker for publishing updates
        """
        self._configs = {}
        self._message_broker = message_broker
        
    async def update_config(self, config_type: str, new_data: Dict[str, Any]) -> None:
        """Update configuration and notify subscribers."""
        try:
            # Update internal config
            if config_type not in self._configs:
                self._configs[config_type] = {}
            self._configs[config_type].update(new_data)
            
            # Publish update if we have a message broker
            if self._message_broker:
                await self._message_broker.publish(
                    f"config/update/{config_type}",
                    {
                        "config_type": config_type,
                        "data": new_data,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            raise
            
    def get_config(self, config_type: str) -> Dict[str, Any]:
        """Get configuration data."""
        try:
            if config_type not in self._configs:
                config_path = Path(f"config/{config_type}.yaml")
                if not config_path.exists():
                    logger.warning(f"Config not found: {config_type}")
                    return {}
                    
                with open(config_path, 'r') as f:
                    self._configs[config_type] = yaml.safe_load(f)
                    
            return self._configs[config_type]
            
        except Exception as e:
            logger.error(f"Error getting config: {e}")
            raise