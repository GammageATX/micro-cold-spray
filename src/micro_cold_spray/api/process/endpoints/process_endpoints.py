"""Process API endpoints."""

from typing import List
from http import HTTPStatus
from fastapi import APIRouter, Depends, Request
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep,
    SequenceResponse,
    SequenceListResponse,
    PatternResponse,
    PatternListResponse,
    ParameterSetResponse,
    ParameterSetListResponse
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

    # Create dependency
    async def get_service() -> ProcessService:
        """Get process service instance.
        
        Returns:
            ProcessService: Process service instance
        """
        return process_service

    @process_router.get("/health", response_model=ServiceHealth)
    async def health(service: ProcessService = Depends(get_service)) -> ServiceHealth:
        """Get service health status.
        
        Returns:
            ServiceHealth: Health status
        """
        return await service.health()

    @process_router.get("/sequences", response_model=SequenceListResponse)
    async def list_sequences(service: ProcessService = Depends(get_service)) -> SequenceListResponse:
        """List available sequences.
        
        Returns:
            SequenceListResponse: List of sequence metadata
            
        Raises:
            HTTPException: If listing fails
        """
        sequences = await service.list_sequences()
        return SequenceListResponse(
            message=f"Retrieved {len(sequences)} sequences",
            sequences=sequences
        )

    @process_router.get("/sequences/{sequence_id}", response_model=SequenceResponse)
    async def get_sequence(
        sequence_id: str,
        service: ProcessService = Depends(get_service)
    ) -> SequenceResponse:
        """Get sequence by ID.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceResponse: Sequence metadata
            
        Raises:
            HTTPException: If sequence not found or retrieval fails
        """
        sequence = await service.get_sequence(sequence_id)
        return SequenceResponse(
            message=f"Retrieved sequence {sequence_id}",
            sequence=sequence
        )

    @process_router.post("/sequences/{sequence_id}/start", response_model=SequenceResponse)
    async def start_sequence(
        sequence_id: str,
        service: ProcessService = Depends(get_service)
    ) -> SequenceResponse:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceResponse: Sequence status
            
        Raises:
            HTTPException: If start fails
        """
        execution_status = await service.start_sequence(sequence_id)
        return SequenceResponse(
            message=f"Started sequence {sequence_id}",
            status=execution_status
        )

    @process_router.post("/sequences/{sequence_id}/stop", response_model=SequenceResponse)
    async def stop_sequence(
        sequence_id: str,
        service: ProcessService = Depends(get_service)
    ) -> SequenceResponse:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceResponse: Sequence status
            
        Raises:
            HTTPException: If stop fails
        """
        execution_status = await service.stop_sequence(sequence_id)
        return SequenceResponse(
            message=f"Stopped sequence {sequence_id}",
            status=execution_status
        )

    @process_router.get("/sequences/{sequence_id}/status", response_model=SequenceResponse)
    async def get_sequence_status(
        sequence_id: str,
        service: ProcessService = Depends(get_service)
    ) -> SequenceResponse:
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence identifier
            
        Returns:
            SequenceResponse: Sequence status
            
        Raises:
            HTTPException: If status check fails
        """
        execution_status = await service.get_sequence_status(sequence_id)
        return SequenceResponse(
            message=f"Status for sequence {sequence_id}: {execution_status}",
            status=execution_status
        )

    @process_router.get("/patterns", response_model=PatternListResponse)
    async def list_patterns(service: ProcessService = Depends(get_service)) -> PatternListResponse:
        """List available patterns.
        
        Returns:
            PatternListResponse: List of patterns
            
        Raises:
            HTTPException: If listing fails
        """
        patterns = await service._pattern.list_patterns()
        return PatternListResponse(
            message=f"Retrieved {len(patterns)} patterns",
            patterns=patterns
        )

    @process_router.get("/parameters", response_model=ParameterSetListResponse)
    async def list_parameter_sets(
        service: ProcessService = Depends(get_service)
    ) -> ParameterSetListResponse:
        """List available parameter sets.
        
        Returns:
            ParameterSetListResponse: List of parameter sets
            
        Raises:
            HTTPException: If listing fails
        """
        parameter_sets = await service._parameter.list_parameter_sets()
        return ParameterSetListResponse(
            message=f"Retrieved {len(parameter_sets)} parameter sets",
            parameter_sets=parameter_sets
        )

    return process_router
