"""Process repository implementation."""

from typing import Dict, Optional, List

from micro_cold_spray.core.process.models.process import ProcessState
from micro_cold_spray.core.errors.exceptions import ProcessError


class ProcessRepository:
    """Process data access repository."""

    def __init__(self):
        """Initialize process repository."""
        self._processes: Dict[str, ProcessState] = {}

    async def get_process(self, process_id: str) -> Optional[ProcessState]:
        """Get process state by ID.
        
        Args:
            process_id: Process identifier
            
        Returns:
            Optional[ProcessState]: Process state if found, None otherwise
            
        Raises:
            ProcessError: If repository operation fails
        """
        try:
            return self._processes.get(process_id)
        except Exception as e:
            raise ProcessError(f"Failed to get process {process_id}: {str(e)}")

    async def save_process(self, process: ProcessState) -> None:
        """Save process state.
        
        Args:
            process: Process state to save
            
        Raises:
            ProcessError: If repository operation fails
        """
        try:
            self._processes[process.process_id] = process
        except Exception as e:
            raise ProcessError(f"Failed to save process {process.process_id}: {str(e)}")

    async def delete_process(self, process_id: str) -> None:
        """Delete process state.
        
        Args:
            process_id: Process identifier
            
        Raises:
            ProcessError: If repository operation fails
        """
        try:
            if process_id in self._processes:
                del self._processes[process_id]
        except Exception as e:
            raise ProcessError(f"Failed to delete process {process_id}: {str(e)}")

    async def list_processes(self) -> List[ProcessState]:
        """List all processes.
        
        Returns:
            List[ProcessState]: List of all process states
            
        Raises:
            ProcessError: If repository operation fails
        """
        try:
            return list(self._processes.values())
        except Exception as e:
            raise ProcessError(f"Failed to list processes: {str(e)}")

    async def clear(self) -> None:
        """Clear all processes.
        
        Raises:
            ProcessError: If repository operation fails
        """
        try:
            self._processes.clear()
        except Exception as e:
            raise ProcessError(f"Failed to clear processes: {str(e)}")
