"""Message broker for system-wide messaging.

Special Note:
    MessageBroker loads its config directly from messaging.yaml to avoid circular dependencies.
    This is an intentional exception to our normal ConfigManager pattern because:
    1. MessageBroker is a core infrastructure component
    2. ConfigManager needs MessageBroker to publish updates
    3. Other components still use ConfigManager as the source of truth
"""
from typing import Any, Callable, Dict, List, Optional, Awaitable
import logging
import yaml
from pathlib import Path
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)

class MessageBroker:
    """Singleton message broker for system-wide messaging."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MessageBroker, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._subscribers: Dict[str, List[Callable]] = {}
            self._message_types = {}
            self._response_futures: Dict[str, asyncio.Future] = {}
            
            # Load initial config
            self._load_config()
            
            # Subscribe to our own config updates
            self.subscribe('config/update/messaging', self._handle_config_update)
            
            self._initialized = True
            logger.info("Message broker initialized")
            
    def _load_config(self) -> None:
        """Load message types from config."""
        try:
            config_path = Path("config/messaging.yaml")
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                    self._message_types = config.get('messaging', {}).get('message_types', {})
                    logger.info("Message types loaded from messaging.yaml")
            else:
                logger.error("messaging.yaml not found")
        except Exception as e:
            logger.error(f"Error loading message types: {e}")
            
    def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle messaging config updates."""
        try:
            if 'message_types' in data:
                self._message_types.update(data['message_types'])
                logger.info("Message types updated from config")
        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            
    def subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to a message topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(callback)
        logger.info(f"Subscribed to topic: {topic}")
        
    async def publish(self, topic: str, data: Any) -> None:
        """Publish a message to subscribers."""
        if topic in self._subscribers:
            for callback in self._subscribers[topic]:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
        logger.info(f"Published to topic: {topic} with data: {data}")
    
    def async_subscribe(self, topic: str, callback: Callable) -> None:
        """Subscribe to a topic with an async callback."""
        if not asyncio.iscoroutinefunction(callback):
            raise ValueError("Callback must be an async function")
        self.subscribe(topic, callback)
    
    async def request(self, topic: str, data: Dict[str, Any], timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Send a request and wait for response.
        
        Args:
            topic: Message topic
            data: Request data
            timeout: Timeout in seconds
            
        Returns:
            Response data or None if timeout/error
        """
        try:
            # Create unique request ID
            request_id = f"{topic}_{datetime.now().timestamp()}"
            
            # Create future for response
            response_future = asyncio.Future()
            self._response_futures[request_id] = response_future
            
            # Add request ID to data
            request_data = {
                **data,
                "timestamp": datetime.now().isoformat()
            }
            
            # Subscribe to response topic
            response_topic = f"{topic}_response"
            
            async def handle_response(response_data: Dict[str, Any]) -> None:
                if topic == "tag/get":
                    tag = data.get("tag")
                    # Simulate getting the tag value from a tag manager or similar component
                    value = self._tag_manager.get_tag(tag)
                    response_data = {
                        "request_id": request_id,
                        "value": value
                    }
                    if not response_future.done():
                        response_future.set_result(response_data)
                if response_data.get("request_id") == request_id:
                    if not response_future.done():
                        response_future.set_result(response_data)
            
            self.subscribe(response_topic, handle_response)
            
            try:
                # Publish request
                await self.publish(topic, request_data)
                
                # Wait for response with timeout
                response = await asyncio.wait_for(response_future, timeout)
                return response
                
            except asyncio.TimeoutError:
                logger.error(f"Request timeout for topic {topic}")
                return None
                
            finally:
                # Clean up
                if request_id in self._response_futures:
                    del self._response_futures[request_id]
                    
        except Exception as e:
            logger.error(f"Error in request: {e}")
            return None