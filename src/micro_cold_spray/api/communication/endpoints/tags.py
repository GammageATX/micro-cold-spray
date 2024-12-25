"""WebSocket endpoints for real-time tag updates."""

from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request, status
from loguru import logger

router = APIRouter(prefix="/ws/communication", tags=["tags"])


@router.websocket("/tags")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for tag updates."""
    try:
        # Get service from app state
        service = websocket.app.state.service
        if not service.is_running:
            await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER)
            return

        # Accept connection
        await websocket.accept()
        logger.info("WebSocket client connected")

        # Subscribe to tag updates
        while True:
            try:
                # Get latest tag values from tag cache service
                tag_values = service._tag_cache.get_all_tag_values()
                
                # Send update
                await websocket.send_json({
                    "type": "tag_update",
                    "data": tag_values
                })

                # Wait for next update
                await websocket.receive_text()

            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {str(e)}")
                break

    except Exception as e:
        logger.error(f"Failed to handle WebSocket connection: {str(e)}")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
