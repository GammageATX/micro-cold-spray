"""Process API endpoints."""

from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from loguru import logger

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
from micro_cold_spray.ui.utils import get_uptime, get_memory_usage


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service status (ok or error)")
    service_name: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    is_running: bool = Field(..., description="Whether service is running")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    error: Optional[str] = Field(None, description="Error message if any")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")


class ProcessRouter:
    """Process API router."""

    def __init__(self, service: ProcessService):
        """Initialize router.
        
        Args:
            service: Process service instance
        """
        self._service = service
        self._router = APIRouter()
        self._init_routes()

    @property
    def router(self) -> APIRouter:
        """Get router instance."""
        return self._router

    def _init_routes(self) -> None:
        """Initialize API routes."""
        # Health check
        self._router.add_api_route(
            "/health",
            self.health_check,
            methods=["GET"],
            response_model=HealthResponse,
            responses={
                status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service unavailable"}
            },
            summary="Health check",
            description="Check service health status"
        )

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

    async def health_check(self) -> HealthResponse:
        """Check service health status."""
        try:
            return HealthResponse(
                status="ok" if self._service.is_running else "error",
                service_name=self._service.name,
                version=self._service.version,
                is_running=self._service.is_running,
                uptime=get_uptime(),
                memory_usage=get_memory_usage(),
                error=None if self._service.is_running else "Service not running",
                timestamp=datetime.now()
            )
        except Exception as e:
            error_msg = f"Health check failed: {str(e)}"
            logger.error(error_msg)
            return HealthResponse(
                status="error",
                service_name=getattr(self._service, "name", "process"),
                version=getattr(self._service, "version", "1.0.0"),
                is_running=False,
                uptime=0.0,
                memory_usage={},
                error=error_msg,
                timestamp=datetime.now()
            )

    async def list_sequences(self) -> List[SequenceMetadata]:
        """List available sequences.
        
        Returns:
            List of sequence metadata
            
        Raises:
            HTTPException: If listing fails (503)
        """
        try:
            return await self._service.get_sequences()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list sequences",
                context={"error": str(e)},
                cause=e
            )

    async def get_current_sequence(self) -> Optional[SequenceMetadata]:
        """Get currently running sequence.
        
        Returns:
            Current sequence metadata if running, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            current_status = await self._service.get_status()
            if current_status == ExecutionStatus.IDLE:
                return None
                
            # Get current sequence from service
            return await self._service.get_current_sequence()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get current sequence",
                context={"error": str(e)},
                cause=e
            )

    async def start_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Start sequence execution.
        
        Args:
            sequence_id: Sequence ID to start
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            # Check if sequence exists
            sequence = await self._service.get_sequence(sequence_id)
            if not sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            # Check if already running
            current_status = await self._service.get_status()
            if current_status != ExecutionStatus.IDLE:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="Another sequence is already running",
                    context={"status": current_status}
                )
                
            # Start sequence
            await self._service.start_sequence(sequence_id)
            return await self._service.get_status()
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to start sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def stop_sequence(self, sequence_id: str) -> ExecutionStatus:
        """Stop sequence execution.
        
        Args:
            sequence_id: Sequence ID to stop
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            # Check if sequence exists
            sequence = await self._service.get_sequence(sequence_id)
            if not sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            # Check if running
            current_status = await self._service.get_status()
            if current_status == ExecutionStatus.IDLE:
                raise create_error(
                    status_code=status.HTTP_409_CONFLICT,
                    message="No sequence is running",
                    context={"status": current_status}
                )
                
            # Stop sequence
            await self._service.stop_sequence(sequence_id)
            return await self._service.get_status()
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to stop sequence",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def get_sequence_status(self, sequence_id: str) -> ExecutionStatus:
        """Get sequence execution status.
        
        Args:
            sequence_id: Sequence ID
            
        Returns:
            Execution status
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            # Check if sequence exists
            sequence = await self._service.get_sequence(sequence_id)
            if not sequence:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Sequence {sequence_id} not found",
                    context={"sequence_id": sequence_id}
                )
                
            return await self._service.get_status()
            
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get sequence status",
                context={"error": str(e), "sequence_id": sequence_id},
                cause=e
            )

    async def list_patterns(self) -> List[ProcessPattern]:
        """List available patterns.
        
        Returns:
            List of patterns
            
        Raises:
            HTTPException: If listing fails (503)
        """
        try:
            return await self._service.get_patterns()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list patterns",
                context={"error": str(e)},
                cause=e
            )

    async def get_pattern(self, pattern_id: str) -> ProcessPattern:
        """Get pattern by ID.
        
        Args:
            pattern_id: Pattern ID
            
        Returns:
            Pattern
            
        Raises:
            HTTPException: If pattern not found (404) or service unavailable (503)
        """
        try:
            pattern = await self._service.get_pattern(pattern_id)
            if not pattern:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Pattern {pattern_id} not found",
                    context={"pattern_id": pattern_id}
                )
            return pattern
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get pattern",
                context={"error": str(e), "pattern_id": pattern_id},
                cause=e
            )

    async def list_parameter_sets(self) -> List[ParameterSet]:
        """List available parameter sets.
        
        Returns:
            List of parameter sets
            
        Raises:
            HTTPException: If listing fails (503)
        """
        try:
            return await self._service.get_parameters()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list parameter sets",
                context={"error": str(e)},
                cause=e
            )

    async def get_parameter_set(self, parameter_set_id: str) -> ParameterSet:
        """Get parameter set by ID.
        
        Args:
            parameter_set_id: Parameter set ID
            
        Returns:
            Parameter set
            
        Raises:
            HTTPException: If parameter set not found (404) or service unavailable (503)
        """
        try:
            parameter_set = await self._service.get_parameter(parameter_set_id)
            if not parameter_set:
                raise create_error(
                    status_code=status.HTTP_404_NOT_FOUND,
                    message=f"Parameter set {parameter_set_id} not found",
                    context={"parameter_set_id": parameter_set_id}
                )
            return parameter_set
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get parameter set",
                context={"error": str(e), "parameter_set_id": parameter_set_id},
                cause=e
            )
