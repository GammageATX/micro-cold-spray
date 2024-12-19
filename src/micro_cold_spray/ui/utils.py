"""UI service utility functions."""

from typing import Dict, List, Optional, Any
from starlette.requests import Request


def flash(request: Request, message: str, category: str = "info") -> None:
    """Add a flash message to the session."""
    if not hasattr(request.session, "flash_messages"):
        request.session["flash_messages"] = []
    request.session["flash_messages"].append({"message": message, "category": category})


def get_flashed_messages(request: Request) -> List[Dict[str, str]]:
    """Get all flash messages and remove them from the session."""
    messages = request.session.get("flash_messages", [])
    request.session["flash_messages"] = []
    return messages


def get_template_context(request: Request, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Get the base template context with flash messages."""
    base_context = {
        "request": request,
        "get_flashed_messages": lambda: get_flashed_messages(request)
    }
    if context:
        base_context.update(context)
    return base_context
