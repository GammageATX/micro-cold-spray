"""Configuration format service implementation."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any

from loguru import logger
from fastapi import status

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.models.config_models import FormatMetadata


class FormatService(BaseService):
    """Configuration format service implementation."""

    _instance = None
    _initialized = False

    def __new__(cls, service_name: str = "format") -> "FormatService":
        """Create or return singleton instance.

        Args:
            service_name: Service name

        Returns:
            Service instance
        """
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, service_name: str = "format") -> None:
        """Initialize service.
        
        Args:
            service_name: Service name
        """
        if self._initialized:
            return

        super().__init__(service_name)
        self._format_validators: Dict[str, Callable] = {}
        self._format_metadata: Dict[str, FormatMetadata] = {}
        self._register_default_validators()
        self._initialized = True

    def _register_default_validators(self) -> None:
        """Register default format validators."""
        self.register_format(
            "12bit",
            self._validate_12bit,
            "12-bit integer value (0-4095)",
            ["0", "2048", "4095"]
        )
        self.register_format(
            "percentage",
            self._validate_percentage,
            "Percentage value (0-100)",
            ["0", "50", "100"]
        )
        self.register_format(
            "ip_address",
            self._validate_ip_address,
            "IPv4 address",
            ["192.168.1.1", "10.0.0.0"]
        )
        self.register_format(
            "hostname",
            self._validate_hostname,
            "Valid hostname",
            ["localhost", "example.com"]
        )
        self.register_format(
            "port",
            self._validate_port,
            "TCP/UDP port number (1-65535)",
            ["80", "8080", "443"]
        )
        self.register_format(
            "path",
            self._validate_path,
            "File system path",
            ["/path/to/file", "C:\\Windows\\System32"]
        )
        self.register_format(
            "tag_path",
            self._validate_tag_path,
            "Tag path (group.subgroup.tag)",
            ["tag", "group.tag"]
        )

    def register_format(
        self,
        format_name: str,
        validator: Callable[[str], bool],
        description: str,
        examples: List[str]
    ) -> None:
        """Register format validator.
        
        Args:
            format_name: Format name
            validator: Validation function
            description: Format description
            examples: Example values
        """
        self._format_validators[format_name] = validator
        self._format_metadata[format_name] = FormatMetadata(
            description=description,
            examples=examples
        )

    def validate_format(self, format_name: str, value: str) -> bool:
        """Validate value against format.
        
        Args:
            format_name: Format name
            value: Value to validate
            
        Returns:
            True if valid
            
        Raises:
            HTTPException: If format not found (404)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        validator = self._format_validators.get(format_name)
        if not validator:
            raise create_error(
                status_code=status.HTTP_404_NOT_FOUND,
                message=f"Format {format_name} not found",
                context={"format": format_name}
            )

        return validator(value)

    def get_format_metadata(self) -> Dict[str, FormatMetadata]:
        """Get format metadata.
        
        Returns:
            Format metadata by name
            
        Raises:
            HTTPException: If service not running (503)
        """
        if not self.is_running:
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message="Service not running",
                context={"service": self.name}
            )

        return self._format_metadata

    def _validate_12bit(self, value: str) -> bool:
        """Validate 12-bit integer value."""
        try:
            val = int(value)
            return 0 <= val <= 4095
        except ValueError:
            return False

    def _validate_percentage(self, value: str) -> bool:
        """Validate percentage value."""
        try:
            val = float(value)
            return 0 <= val <= 100
        except ValueError:
            return False

    def _validate_ip_address(self, value: str) -> bool:
        """Validate IPv4 address."""
        pattern = r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
        return bool(re.match(pattern, value))

    def _validate_hostname(self, value: str) -> bool:
        """Validate hostname."""
        pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
        return bool(re.match(pattern, value))

    def _validate_port(self, value: str) -> bool:
        """Validate TCP/UDP port number."""
        try:
            val = int(value)
            return 1 <= val <= 65535
        except ValueError:
            return False

    def _validate_path(self, value: str) -> bool:
        """Validate file system path."""
        try:
            Path(value)
            return True
        except Exception:
            return False

    def _validate_tag_path(self, value: str) -> bool:
        """Validate tag path."""
        pattern = r"^[a-zA-Z][a-zA-Z0-9_]*(?:\.[a-zA-Z][a-zA-Z0-9_]*)*$"
        return bool(re.match(pattern, value))
