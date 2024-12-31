"""Sequence control endpoints."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPStatus, status, Depends
from loguru import logger
import asyncio

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.dependencies import get_process_service
from micro_cold_spray.api.process.models.process_models import (
    SequenceStatus,
    MessageResponse,
    SequenceListResponse
)

router = APIRouter(prefix="/sequences", tags=["sequences"])


@router.get(
    "",
    response_model=SequenceListResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to list sequences"}
    }
)
async def list_sequences(
    service: ProcessService = Depends(get_process_service)
) -> SequenceListResponse:
    """List available sequences."""
    try:
        sequences = await service.sequence_service.list_sequences()
        return SequenceListResponse(sequences=sequences)
    except Exception as e:
        logger.error(f"Failed to list sequences: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to list sequences: {str(e)}"
        )


@router.post(
    "/{sequence_id}/start",
    response_model=MessageResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"},
        status.HTTP_409_CONFLICT: {"description": "Sequence already running"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to start sequence"}
    }
)
async def start_sequence(
    sequence_id: str,
    service: ProcessService = Depends(get_process_service)
) -> MessageResponse:
    """Start sequence execution."""
    try:
        await service.sequence_service.start_sequence(sequence_id)
        return MessageResponse(message=f"Sequence {sequence_id} started")
    except Exception as e:
        logger.error(f"Failed to start sequence {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to start sequence: {str(e)}"
        )


@router.post(
    "/{sequence_id}/stop",
    response_model=MessageResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to stop sequence"}
    }
)
async def stop_sequence(
    sequence_id: str,
    service: ProcessService = Depends(get_process_service)
) -> MessageResponse:
    """Stop sequence execution."""
    try:
        await service.sequence_service.stop_sequence(sequence_id)
        return MessageResponse(message=f"Sequence {sequence_id} stopped")
    except Exception as e:
        logger.error(f"Failed to stop sequence {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to stop sequence: {str(e)}"
        )


@router.get(
    "/{sequence_id}/status",
    response_model=SequenceStatus,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Failed to get status"}
    }
)
async def get_status(
    sequence_id: str,
    service: ProcessService = Depends(get_process_service)
) -> SequenceStatus:
    """Get sequence status."""
    try:
        return await service.sequence_service.get_status(sequence_id)
    except Exception as e:
        logger.error(f"Failed to get sequence status {sequence_id}: {e}")
        raise create_error(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Failed to get sequence status: {str(e)}"
        )


@router.websocket("/ws/{sequence_id}")
async def sequence_status(
    websocket: WebSocket,
    sequence_id: str
):
    """WebSocket endpoint for sequence status updates."""
    try:
        service = websocket.app.state.service
        if not service.is_running:
            await websocket.close(code=HTTPStatus.SERVICE_UNAVAILABLE)
            return

        await websocket.accept()
        logger.info(f"Sequence {sequence_id} WebSocket client connected")

        # Create queue for status updates
        status_queue = asyncio.Queue()
        
        # Subscribe to status updates
        def status_changed(sequence_status: SequenceStatus):
            asyncio.create_task(status_queue.put(sequence_status))
        
        service.sequence_service.on_status_changed(sequence_id, status_changed)

        try:
            while True:
                sequence_status = await status_queue.get()
                await websocket.send_json({
                    "type": "sequence_status",
                    "data": sequence_status.dict()
                })

        except WebSocketDisconnect:
            logger.info(f"Sequence {sequence_id} WebSocket client disconnected")
        finally:
            service.sequence_service.remove_status_changed_callback(sequence_id, status_changed)

    except Exception as e:
        logger.error(f"Sequence WebSocket error: {str(e)}")
        await websocket.close(code=HTTPStatus.INTERNAL_SERVER_ERROR)
