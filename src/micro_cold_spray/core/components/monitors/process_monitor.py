"""Process monitoring component."""
from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.tags.tag_manager import TagManager
from ...exceptions import MonitorError

class ProcessMonitor:
    """Monitors process status and publishes updates."""

    def __init__(self, tag_manager: TagManager, message_broker: MessageBroker):
        """
        Initialize monitor.
        
        Args:
            tag_manager: Tag manager instance
            message_broker: Message broker instance
        """
        self._tag_manager = tag_manager
        self._message_broker = message_broker
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("Process monitor initialized")

    async def start(self) -> None:
        """Start monitoring process status."""
        try:
            if self._is_running:
                logger.warning("Process monitor already running")
                return

            self._is_running = True
            
            # Subscribe to process-related messages
            await self._message_broker.subscribe(
                "process/status",
                self._handle_process_status
            )
            
            # Start monitoring task
            self._monitoring_task = asyncio.create_task(self._monitor_process())
            logger.info("Process monitoring started")

        except Exception as e:
            logger.exception("Failed to start process monitoring")
            raise MonitorError(f"Process monitor start failed: {str(e)}") from e

    async def stop(self) -> None:
        """Stop monitoring process status."""
        try:
            self._is_running = False
            
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                
            logger.info("Process monitoring stopped")

        except Exception as e:
            logger.exception("Error stopping process monitor")
            raise MonitorError(f"Process monitor stop failed: {str(e)}") from e

    async def _handle_process_status(self, data: Dict[str, Any]) -> None:
        """Handle process status updates."""
        try:
            # Update process status tags
            for parameter, value in data.items():
                await self._tag_manager.set_tag(f"process.status.{parameter}", value)
                
            # Publish consolidated status
            await self._message_broker.publish(
                "process/status/updated",
                {
                    "status": data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling process status: {e}")
            await self._message_broker.publish("process/status/error", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _monitor_process(self) -> None:
        """Monitor process status continuously."""
        try:
            while self._is_running:
                try:
                    # Monitor process parameters
                    pressure = await self._tag_manager.get_tag("process.pressure")
                    temperature = await self._tag_manager.get_tag("process.temperature")
                    flow_rate = await self._tag_manager.get_tag("process.flow_rate")
                    
                    await self._message_broker.publish(
                        "process/status",
                        {
                            "pressure": pressure,
                            "temperature": temperature,
                            "flow_rate": flow_rate,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    await asyncio.sleep(0.1)  # Process monitoring rate
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in process monitoring: {e}")
                    await asyncio.sleep(1.0)  # Error recovery delay
                    
        except asyncio.CancelledError:
            logger.info("Process monitoring cancelled")
            raise
        except Exception as e:
            logger.exception("Fatal error in process monitoring")
            raise MonitorError(f"Process monitoring failed: {str(e)}") from e