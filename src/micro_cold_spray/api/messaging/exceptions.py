"""Messaging service exceptions."""

from typing import Dict, Any, Optional
from ..base.exceptions import ServiceError


class MessagingError(ServiceError):
    """Base class for messaging errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, context)


class TopicError(MessagingError):
    """Raised for topic-related errors."""
    pass


class PublishError(MessagingError):
    """Raised when message publishing fails."""
    pass


class SubscriptionError(MessagingError):
    """Raised when subscription operations fail."""
    pass


class RequestError(MessagingError):
    """Raised when request/response operations fail."""
    pass


class WebSocketError(MessagingError):
    """Raised for WebSocket-specific errors."""
    pass
