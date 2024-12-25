"""Communication API endpoints."""

from typing import Dict, Any
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, status
from loguru import logger
import asyncio

from micro_cold_spray.utils.errors import create_error


router = APIRouter()


@router.websocket("/ws/state")
async def websocket_state(websocket: WebSocket):
    """WebSocket endpoint for combined system state updates.
    Provides real-time updates for both equipment and motion state changes."""
    try:
        # Get service from app state
        service = websocket.app.state.service
        if not service.is_running:
            await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
            return

        # Accept connection
        await websocket.accept()
        logger.info("System state WebSocket client connected")

        # Create queues for state updates
        equipment_queue = asyncio.Queue()
        motion_queue = asyncio.Queue()
        
        # Subscribe to state updates
        def equipment_state_changed(state: Dict[str, Any]):
            asyncio.create_task(equipment_queue.put(state))
            
        def motion_state_changed(state: Dict[str, Any]):
            asyncio.create_task(motion_queue.put(state))
        
        # Register callbacks
        service.equipment.on_state_changed(equipment_state_changed)
        service.motion.on_state_changed(motion_state_changed)

        try:
            # Send initial state
            equipment_state = await service.equipment.get_state()
            motion_position = await service.motion.get_position()
            motion_status = await service.motion.get_status()
            
            await websocket.send_json({
                "type": "state_update",
                "data": {
                    "equipment": equipment_state.dict(),
                    "motion": {
                        "position": motion_position.dict(),
                        "status": motion_status.dict()
                    }
                }
            })

            # Wait for state updates
            while True:
                try:
                    # Wait for either equipment or motion update
                    done, pending = await asyncio.wait(
                        [
                            asyncio.create_task(equipment_queue.get()),
                            asyncio.create_task(motion_queue.get())
                        ],
                        return_when=asyncio.FIRST_COMPLETED
                    )
                    
                    # Cancel pending tasks
                    for task in pending:
                        task.cancel()
                    
                    # Get latest states
                    equipment_state = await service.equipment.get_state()
                    motion_position = await service.motion.get_position()
                    motion_status = await service.motion.get_status()
                    
                    # Send update
                    await websocket.send_json({
                        "type": "state_update",
                        "data": {
                            "equipment": equipment_state.dict(),
                            "motion": {
                                "position": motion_position.dict(),
                                "status": motion_status.dict()
                            }
                        }
                    })

                except WebSocketDisconnect:
                    logger.info("System state WebSocket client disconnected")
                    break
                except Exception as e:
                    logger.error(f"System state WebSocket error: {str(e)}")
                    break

        finally:
            # Unregister callbacks when connection closes
            service.equipment.remove_state_changed_callback(equipment_state_changed)
            service.motion.remove_state_changed_callback(motion_state_changed)

    except Exception as e:
        logger.error(f"Failed to handle system state WebSocket connection: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)

__all__ = ["router"]
