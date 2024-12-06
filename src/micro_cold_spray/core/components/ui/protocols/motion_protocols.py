"""Motion-related protocols."""
from typing import Dict, Protocol, runtime_checkable


@runtime_checkable
class MotionControlProtocol(Protocol):
    """Protocol for motion control interface."""

    async def handle_jog_command(
        self,
        axis: str,
        direction: int,
        speed: float,
        step_size: float
    ) -> None:
        """Handle jog command."""
        ...

    async def handle_stop_command(self) -> None:
        """Handle stop command."""
        ...

    async def handle_move_command(self, position: Dict[str, float]) -> None:
        """Handle move command to absolute position."""
        ...
