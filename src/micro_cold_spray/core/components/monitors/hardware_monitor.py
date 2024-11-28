"""Hardware monitoring component."""
from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from datetime import datetime

from ...infrastructure.messaging.message_broker import MessageBroker
from ...infrastructure.tags.tag_manager import TagManager
from ...exceptions import MonitorError

class HardwareMonitor:
    """Monitors hardware connections and status."""

    def __init__(self, message_broker: MessageBroker, tag_manager: TagManager):
        """
        Initialize monitor.
        
        Args:
            message_broker: Message broker instance
            tag_manager: Tag manager instance
        """
        self._message_broker = message_broker
        self._tag_manager = tag_manager
        self._monitoring_task: Optional[asyncio.Task] = None
        self._is_running = False
        
        logger.info("Hardware monitor initialized")

    async def start(self) -> None:
        """Start hardware monitoring."""
        try:
            # Test initial connections
            connection_status = await self._tag_manager.test_connections()
            
            # Publish initial status
            for device, connected in connection_status.items():
                await self._message_broker.publish(
                    "hardware/connection",
                    {
                        "device": device,
                        "connected": connected,
                        "timestamp": datetime.now().isoformat()
                    }
                )
                
            if not all(connection_status.values()):
                logger.warning("Not all hardware devices connected")
                await self._message_broker.publish("error", {
                    "error": "Hardware initialization incomplete",
                    "topic": "hardware/init",
                    "details": connection_status
                })
            
            self._is_running = True
            logger.info("Hardware monitor started")
            
        except Exception as e:
            logger.error(f"Failed to start hardware monitor: {e}")
            await self._message_broker.publish("error", {
                "error": str(e),
                "topic": "hardware/monitor",
                "action": "start"
            })

    async def stop(self) -> None:
        """Stop monitoring hardware status."""
        try:
            self._is_running = False
            
            if self._monitoring_task:
                self._monitoring_task.cancel()
                try:
                    await self._monitoring_task
                except asyncio.CancelledError:
                    pass
                
            logger.info("Hardware monitoring stopped")

        except Exception as e:
            logger.exception("Error stopping hardware monitor")
            raise MonitorError(f"Hardware monitor stop failed: {str(e)}") from e

    async def _handle_hardware_status(self, data: Dict[str, Any]) -> None:
        """Handle hardware status updates."""
        try:
            # Update hardware status tags
            for component, status in data.items():
                await self._tag_manager.set_tag(f"hardware.status.{component}", status)
                
            # Publish consolidated status
            await self._message_broker.publish(
                "hardware/status/updated",
                {
                    "status": data,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error handling hardware status: {e}")
            await self._message_broker.publish("hardware/status/error", {
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

    async def _monitor_hardware(self) -> None:
        """Monitor hardware status continuously."""
        try:
            while self._is_running:
                try:
                    # Check hardware connections
                    plc_connected = await self._tag_manager.get_tag("hardware.plc.connected")
                    ssh_connected = await self._tag_manager.get_tag("hardware.ssh.connected")
                    
                    await self._message_broker.publish(
                        "hardware/status",
                        {
                            "plc": plc_connected,
                            "ssh": ssh_connected,
                            "timestamp": datetime.now().isoformat()
                        }
                    )
                    
                    await asyncio.sleep(1.0)  # Status check interval
                    
                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error in hardware monitoring: {e}")
                    await asyncio.sleep(5.0)  # Error recovery delay
                    
        except asyncio.CancelledError:
            logger.info("Hardware monitoring cancelled")
            raise
        except Exception as e:
            logger.exception("Fatal error in hardware monitoring")
            raise MonitorError(f"Hardware monitoring failed: {str(e)}") from e