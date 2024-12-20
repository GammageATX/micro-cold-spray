"""Process API endpoints."""

from typing import Dict, Any, List, Optional

from fastapi import APIRouter, status

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.base.base_router import BaseRouter
from micro_cold_spray.api.process.process_service import ProcessService


class ProcessRouter(BaseRouter):
    """Process API router."""

    def __init__(self, process_service: ProcessService) -> None:
        """Initialize router.
        
        Args:
            process_service: Process service
        """
        super().__init__()
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
            response_model=List[Dict[str, Any]],
            summary="List sequences",
            description="List available sequences"
        )
        self._router.add_api_route(
            "/sequences/current",
            self.get_current_sequence,
            methods=["GET"],
            response_model=Optional[Dict[str, Any]],
            summary="Get current sequence",
            description="Get currently running sequence"
        )
        self._router.add_api_route(
            "/sequences/{sequence_id}/start",
            self.start_sequence,
            methods=["POST"],
            status_code=status.HTTP_202_ACCEPTED,
            summary="Start sequence",
            description="Start spray sequence"
        )
        self._router.add_api_route(
            "/sequences/abort",
            self.abort_sequence,
            methods=["POST"],
            status_code=status.HTTP_202_ACCEPTED,
            summary="Abort sequence",
            description="Abort currently running sequence"
        )

        # Pattern routes
        self._router.add_api_route(
            "/patterns",
            self.list_patterns,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="List patterns",
            description="List available patterns"
        )

        # Parameter routes
        self._router.add_api_route(
            "/parameters",
            self.list_parameter_sets,
            methods=["GET"],
            response_model=List[Dict[str, Any]],
            summary="List parameter sets",
            description="List available parameter sets"
        )

        # Action routes
        self._router.add_api_route(
            "/actions/current",
            self.get_current_action,
            methods=["GET"],
            response_model=Optional[Dict[str, Any]],
            summary="Get current action",
            description="Get currently executing action"
        )

    async def list_sequences(self) -> List[Dict[str, Any]]:
        """List sequences.
        
        Returns:
            List of sequences
            
        Raises:
            HTTPException: If service unavailable (503)
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

    async def get_current_sequence(self) -> Optional[Dict[str, Any]]:
        """Get current sequence.
        
        Returns:
            Current sequence if running, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._process_service.get_current_sequence()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get current sequence",
                context={"error": str(e)},
                cause=e
            )

    async def start_sequence(self, sequence_id: str) -> None:
        """Start sequence.
        
        Args:
            sequence_id: Sequence ID to start
            
        Raises:
            HTTPException: If sequence not found (404) or service unavailable (503)
        """
        try:
            await self._process_service.start_sequence(sequence_id)
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start sequence {sequence_id}",
                context={
                    "sequence_id": sequence_id,
                    "error": str(e)
                },
                cause=e
            )

    async def abort_sequence(self) -> None:
        """Abort sequence.
        
        Raises:
            HTTPException: If no sequence running (404) or service unavailable (503)
        """
        try:
            await self._process_service.abort_sequence()
        except Exception as e:
            if isinstance(e, create_error):
                raise e
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to abort sequence",
                context={"error": str(e)},
                cause=e
            )

    async def list_patterns(self) -> List[Dict[str, Any]]:
        """List patterns.
        
        Returns:
            List of patterns
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._process_service.list_patterns()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list patterns",
                context={"error": str(e)},
                cause=e
            )

    async def list_parameter_sets(self) -> List[Dict[str, Any]]:
        """List parameter sets.
        
        Returns:
            List of parameter sets
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._process_service.list_parameter_sets()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to list parameter sets",
                context={"error": str(e)},
                cause=e
            )

    async def get_current_action(self) -> Optional[Dict[str, Any]]:
        """Get current action.
        
        Returns:
            Current action if executing, None otherwise
            
        Raises:
            HTTPException: If service unavailable (503)
        """
        try:
            return await self._process_service.get_current_action()
        except Exception as e:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Failed to get current action",
                context={"error": str(e)},
                cause=e
            )

    @property
    def router(self) -> APIRouter:
        """Get router.
        
        Returns:
            FastAPI router
        """
        return self._router
