"""Format validation service."""

import re
from typing import Dict, Any, Optional, Callable, NamedTuple
from pathlib import Path
from loguru import logger

from ...base import BaseService
from ..models import ConfigValidationResult
from ..exceptions import ConfigurationError


class FormatMetadata(NamedTuple):
    """Format validator metadata."""
    description: str
    examples: list[str]


class FormatService(BaseService):
    """Service for validating special data formats."""

    def __init__(self):
        """Initialize format service."""
        super().__init__(service_name="format")
        self._format_validators: Dict[str, Callable] = {}
        self._format_metadata: Dict[str, FormatMetadata] = {}
        self._register_default_validators()

    async def _start(self) -> None:
        """Start format service."""
        try:
            logger.info(
                f"Format service started with {len(self._format_validators)} validators"
            )
        except Exception as e:
            raise ConfigurationError("Failed to start format service", {"error": str(e)})

    def register_format(
        self,
        format_type: str,
        validator: Callable,
        description: str,
        examples: list[str]
    ) -> None:
        """Register a new format validator.
        
        Args:
            format_type: Format identifier
            validator: Validation function
            description: Format description
            examples: Example valid values
            
        Raises:
            ConfigurationError: If registration fails
        """
        try:
            if format_type in self._format_validators:
                raise ConfigurationError(
                    f"Format {format_type} already registered",
                    {"format": format_type}
                )
            
            self._format_validators[format_type] = validator
            self._format_metadata[format_type] = FormatMetadata(
                description=description,
                examples=examples
            )
            logger.debug(f"Registered format validator: {format_type}")
            
        except Exception as e:
            raise ConfigurationError(
                "Failed to register format",
                {
                    "format": format_type,
                    "error": str(e)
                }
            )

    def get_format_info(self, format_type: str) -> Optional[FormatMetadata]:
        """Get format metadata.
        
        Args:
            format_type: Format to get info for
            
        Returns:
            Format metadata if found
        """
        return self._format_metadata.get(format_type)

    @property
    def available_formats(self) -> list[str]:
        """Get list of available format validators."""
        return list(self._format_validators.keys())

    async def validate(
        self,
        data: Any,
        format_type: str,
        path: str = ""
    ) -> ConfigValidationResult:
        """Validate data against format.
        
        Args:
            data: Data to validate
            format_type: Format to validate against
            path: Path for error messages
            
        Returns:
            Validation result
            
        Raises:
            ConfigurationError: If validation fails
        """
        errors = []
        warnings = []

        try:
            validator = self._format_validators.get(format_type)
            if validator:
                error = validator(data)
                if error:
                    errors.append(f"{path}: {error}")
            else:
                warnings.append(f"{path}: Unknown format {format_type}")

        except Exception as e:
            raise ConfigurationError(
                "Format validation failed",
                {
                    "format": format_type,
                    "path": path,
                    "error": str(e)
                }
            )

        return ConfigValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _register_default_validators(self) -> None:
        """Register default format validators."""
        # Numeric formats
        self.register_format(
            "12bit_linear",
            self._validate_12bit,
            "12-bit linear value (0-4095)",
            ["0", "2048", "4095"]
        )
        
        self.register_format(
            "12bit_dac",
            self._validate_12bit,
            "12-bit DAC value (0-4095)",
            ["0", "2048", "4095"]
        )
        
        self.register_format(
            "percentage",
            self._validate_percentage,
            "Percentage value (0-100)",
            ["0", "50", "100"]
        )

        # Network formats
        self.register_format(
            "ip_address",
            self._validate_ip_address,
            "IPv4 address",
            ["192.168.1.1", "10.0.0.1"]
        )
        
        self.register_format(
            "port",
            self._validate_port,
            "Network port (1-65535)",
            ["80", "443", "8080"]
        )
        
        self.register_format(
            "hostname",
            self._validate_hostname,
            "Network hostname",
            ["localhost", "example.com"]
        )

        # Path formats
        self.register_format(
            "path",
            self._validate_path,
            "File system path",
            ["C:/path/to/file", "/usr/local/bin"]
        )
        
        self.register_format(
            "tag_path",
            self._validate_tag_path,
            "Tag path (group.subgroup.tag)",
            ["system.sensors.temp", "control.valves.inlet"]
        )

    def _validate_12bit(self, value: Any) -> Optional[str]:
        """Validate 12-bit value (0-4095)."""
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num_value = float(value)
            if not 0 <= num_value <= 4095:
                return "Value must be between 0 and 4095"
        except Exception:
            return "Invalid numeric value"
        return None

    def _validate_percentage(self, value: Any) -> Optional[str]:
        """Validate percentage value (0-100)."""
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num_value = float(value)
            if not 0 <= num_value <= 100:
                return "Value must be between 0 and 100"
        except Exception:
            return "Invalid numeric value"
        return None

    def _validate_ip_address(self, value: str) -> Optional[str]:
        """Validate IP address format."""
        if not isinstance(value, str):
            return "Value must be string"
            
        pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
        if not re.match(pattern, value):
            return "Invalid IP address format"
            
        # Validate each octet
        octets = value.split(".")
        for octet in octets:
            if not 0 <= int(octet) <= 255:
                return "IP address octets must be between 0 and 255"
                
        return None

    def _validate_hostname(self, value: str) -> Optional[str]:
        """Validate hostname format."""
        if not isinstance(value, str):
            return "Value must be string"
            
        pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
        if not re.match(pattern, value):
            return "Invalid hostname format"
            
        if len(value) > 255:
            return "Hostname too long (max 255 characters)"
            
        return None

    def _validate_port(self, value: Any) -> Optional[str]:
        """Validate port number."""
        try:
            if not isinstance(value, int):
                return "Port must be integer"
            if not 1 <= value <= 65535:
                return "Port must be between 1 and 65535"
        except Exception:
            return "Invalid port number"
        return None

    def _validate_path(self, value: str) -> Optional[str]:
        """Validate file/directory path."""
        if not isinstance(value, str):
            return "Path must be string"
            
        try:
            path = Path(value)
            
            # Basic path validation
            if not value or value.isspace():
                return "Path cannot be empty"
                
            invalid_chars = '<>"|?*'
            if any(c in value for c in invalid_chars):
                return f"Path contains invalid characters: {invalid_chars}"
                
            # Check path length
            if len(str(path)) > 260:  # Windows MAX_PATH
                return "Path too long"
                
        except Exception:
            return "Invalid path format"
            
        return None

    def _validate_tag_path(self, value: str) -> Optional[str]:
        """Validate tag path format (group.subgroup.tag)."""
        if not isinstance(value, str):
            return "Tag path must be string"
            
        pattern = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"
        if not re.match(pattern, value):
            return "Invalid tag path format"
            
        # Check depth and length
        parts = value.split(".")
        if len(parts) > 10:
            return "Tag path too deep (max 10 levels)"
        if len(value) > 255:
            return "Tag path too long (max 255 characters)"
            
        return None
