"""Process API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, status
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep
)


def create_process_router(process_service: ProcessService) -> APIRouter:
    """Create process router with service instance.
    
    Args:
        process_service: Process service instance
        
    Returns:
        Process router
    """
    # Create router
    process_router = APIRouter(prefix="/process", tags=["process"])

    @process_router.get("/sequences", response_model=List[SequenceMetadata])
    async def list_sequences():
        """List available sequences.
        
        Returns:
            List of sequence metadata
            
        Raises:
            HTTPException: If listing fails
        """
        return await process_service.list_sequences()

    @process_router.get("/sequences/{sequence_id}", response_model=SequenceMetadata)
    async def get_sequence(sequence_id: str):
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Sequence metadata
            
        Raises:
            HTTPException: If sequence not found or retrieval fails
        """
        return await process_service.get_sequence(sequence_id)

    @process_router.post("/sequences/{sequence_id}/start", response_model=ExecutionStatus)
    async def start_sequence(sequence_id: str):
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If start fails
        """
        return await process_service.start_sequence(sequence_id)

    @process_router.post("/sequences/{sequence_id}/stop", response_model=ExecutionStatus)
    async def stop_sequence(sequence_id: str):
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If stop fails
        """
        return await process_service.stop_sequence(sequence_id)

    @process_router.get("/sequences/{sequence_id}/status", response_model=ExecutionStatus)
    async def get_sequence_status(sequence_id: str):
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If status check fails
        """
        return await process_service.get_sequence_status(sequence_id)

    return process_router
