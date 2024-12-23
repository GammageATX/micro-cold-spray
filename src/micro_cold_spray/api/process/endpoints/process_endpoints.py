"""Process API endpoints."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from fastapi import APIRouter, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus,
    ActionStatus,
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep
)


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    is_running: bool
    timestamp: datetime


class ProcessRouter:
    """Process API router."""

    def __init__(self, process_service: ProcessService) -> None:
        """Initialize router.
        
        Args:
            process_service: Process service
        """
        self._process_service = process_service
        self._router = APIRouter(
            prefix="/process",
            tags=["process"]
        )
        self._init_routes()

    def _init_routes(self) -> None:
        """Initialize routes."""
        # Sequence routes
        self._router.add_api_route(
            "/sequences",
            self.list_sequences,
            methods=["GET"],
            response_model=List[SequenceMetadata],
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
            },
            summary="List sequences",
            description="List available sequences"
        )
        self._router.add_api_route(
            "/sequences/current",
            self.get_current_sequence,
            methods=["GET"],
            response_model=Optional[SequenceMetadata],
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "No sequence running"}
            },
            summary="Get current sequence",
            description="Get currently running sequence"
        )
        self._router.add_api_route(
            "/sequences/{sequence_id}/start",
            self.start_sequence,
            methods=["POST"],
            response_model=ExecutionStatus,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"},
                status.HTTP_409_CONFLICT: {"description": "Sequence already running"}
            },
            summary="Start sequence",
            description="Start sequence execution"
        )
        self._router.add_api_route(
            "/sequences/{sequence_id}/stop",
            self.stop_sequence,
            methods=["POST"],
            response_model=ExecutionStatus,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"},
                status.HTTP_409_CONFLICT: {"description": "No sequence running"}
            },
            summary="Stop sequence",
            description="Stop sequence execution"
        )
        self._router.add_api_route(
            "/sequences/{sequence_id}/status",
            self.get_sequence_status,
            methods=["GET"],
            response_model=ExecutionStatus,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "Sequence not found"}
            },
            summary="Get sequence status",
            description="Get sequence execution status"
        )

        # Pattern routes
        self._router.add_api_route(
            "/patterns",
            self.list_patterns,
            methods=["GET"],
            response_model=List[ProcessPattern],
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
            },
            summary="List patterns",
            description="List available patterns"
        )
        self._router.add_api_route(
            "/patterns/{pattern_id}",
            self.get_pattern,
            methods=["GET"],
            response_model=ProcessPattern,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "Pattern not found"}
            },
            summary="Get pattern",
            description="Get pattern by ID"
        )

        # Parameter routes
        self._router.add_api_route(
            "/parameters",
            self.list_parameter_sets,
            methods=["GET"],
            response_model=List[ParameterSet],
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
            },
            summary="List parameter sets",
            description="List available parameter sets"
        )
        self._router.add_api_route(
            "/parameters/{parameter_set_id}",
            self.get_parameter_set,
            methods=["GET"],
            response_model=ParameterSet,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"},
                status.HTTP_404_NOT_FOUND: {"description": "Parameter set not found"}
            },
            summary="Get parameter set",
            description="Get parameter set by ID"
        )

    @property
    def router(self) -> APIRouter:
        """Get router.
        
        Returns:
            APIRouter instance
        """
        return self._router

    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List of sequence metadata
            
        Raises:
            HTTPException: If listing fails (503)
        """
        try:
            return await self._process_service.list_sequences()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list sequences",
                context={"error": str(e)},
                cause=e
            )
            
    # ... rest of the endpoint implementations ...
