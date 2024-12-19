"""Configuration format service implementation."""

import re
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from loguru import logger

from micro_cold_spray.api.base.base_service import BaseService
from micro_cold_spray.api.base.base_exceptions import ConfigError, ValidationError
from micro_cold_spray.api.config.models.config_models import FormatMetadata


class ConfigFormatService(BaseService):
    """Configuration format service implementation."""

    _instance = None
    _initialized = False

    def __new__(cls, service_name: str = "format") -> "ConfigFormatService":
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

    async def _start(self) -> None:
        """Start format service."""
        try:
            logger.info("Format service started with {} formats", len(self._format_validators))
        except Exception as e:
            raise ConfigError("Failed to start format service", {"error": str(e)})

    async def start(self) -> None:
        """Start service.

        Raises:
            ConfigError: If service fails to start
        """
        if self.is_running:
            return

        try:
            await self._start()
            self._is_running = True
            self._is_initialized = True
            self._start_time = datetime.now()
            self._metrics["start_count"] += 1
        except Exception as e:
            self._metrics["error_count"] += 1
            self._metrics["last_error"] = str(e)
            raise ConfigError("Failed to start format service") from e

    def register_format(self, format_type: str, validator: Callable, description: str, examples: List[str]) -> None:
        """Register format validator.

        Args:
            format_type: Format type
            validator: Validator function
            description: Format description
            examples: Example values

        Raises:
            ConfigError: If format already exists or registration fails
        """
        if format_type in self._format_validators:
            raise ConfigError("Format already registered", {"format": format_type})

        try:
            metadata = FormatMetadata(
                description=description,
                examples=examples
            )
            self._format_validators[format_type] = validator
            self._format_metadata[format_type] = metadata
        except Exception as e:
            raise ConfigError("Failed to register format", {"error": str(e)})

    def validate_format(self, format_type: str, value: Any) -> None:
        """Validate format.

        Args:
            format_type: Format type
            value: Value to validate

        Raises:
            ValidationError: If validation fails
        """
        if format_type not in self._format_validators:
            raise ValidationError(
                "Unknown format type",
                {
                    "format": format_type,
                    "available_formats": list(self._format_validators.keys())
                }
            )

        try:
            validator = self._format_validators[format_type]
            error = validator(value)
            if error:
                raise ValidationError("Format validation failed", {"error": error})
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError("Format validation failed", {"error": str(e)})

    def _validate_12bit(self, value: Any) -> Optional[str]:
        """Validate 12-bit value.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num = float(value)
            if not 0 <= num <= 4095:
                return "Value must be between 0 and 4095"
            return None
        except Exception as e:
            return f"Validation failed: {str(e)}"

    def _validate_percentage(self, value: Any) -> Optional[str]:
        """Validate percentage value.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num = float(value)
            if not 0 <= num <= 100:
                return "Value must be between 0 and 100"
            return None
        except Exception as e:
            return f"Validation failed: {str(e)}"

    def _validate_ip_address(self, value: Any) -> Optional[str]:
        """Validate IP address.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, str):
                return "Value must be string"

            pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            if not re.match(pattern, value):
                return "Invalid IP address format"

            parts = value.split(".")
            for part in parts:
                num = int(part)
                if not 0 <= num <= 255:
                    return "Value must be between 0 and 255"
            return None
        except Exception as e:
            return f"Invalid IP address format: {str(e)}"

    def _validate_hostname(self, value: Any) -> Optional[str]:
        """Validate hostname.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, str):
                return "Value must be string"

            if len(value) > 255:
                return "Hostname too long"

            for label in value.split("."):
                if len(label) > 63:
                    return "Label too long"
                if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", label):
                    return "Invalid hostname format"
            return None
        except Exception as e:
            return f"Validation failed: {str(e)}"

    def _validate_port(self, value: Any) -> Optional[str]:
        """Validate port number.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, int):
                return "Port must be integer"
            if not 1 <= value <= 65535:
                return "Port must be between 1 and 65535"
            return None
        except Exception as e:
            return f"Validation failed: {str(e)}"

    def _validate_path(self, value: Any) -> Optional[str]:
        """Validate file system path.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, str):
                return "Value must be string"

            if not value.strip():
                return "Path cannot be empty"

            if len(value) > 260:
                return "Path too long"

            try:
                path = Path(value)
                if ".." in path.parts:
                    return "Path cannot contain parent directory references"
            except Exception as e:
                return f"Invalid path format: {str(e)}"

            # Allow backslashes for Windows paths
            invalid_chars = '<>"|?*'
            if any(c in value for c in invalid_chars):
                return "Path contains invalid characters"

            return None
        except Exception as e:
            return f"Invalid path format: {str(e)}"

    def _validate_tag_path(self, value: Any) -> Optional[str]:
        """Validate tag path.

        Args:
            value: Value to validate

        Returns:
            Error message if validation fails
        """
        try:
            if not isinstance(value, str):
                return "Value must be string"

            if len(value) > 255:
                return "Tag path too long"

            pattern = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"
            if not re.match(pattern, value):
                return "Invalid tag path format"

            return None
        except Exception as e:
            return f"Invalid tag path format: {str(e)}"
