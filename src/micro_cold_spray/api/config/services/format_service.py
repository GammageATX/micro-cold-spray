"""Format service for configuration validation."""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List

from loguru import logger

from micro_cold_spray.api.base import BaseService
from micro_cold_spray.api.base.exceptions import ConfigurationError, ValidationError
from micro_cold_spray.api.config.models import FormatMetadata


class FormatService(BaseService):
    """Service for validating special data formats."""

    # Singleton instance
    _instance = None
    _initialized = False

    def __new__(cls):
        """Ensure only one instance is created."""
        if cls._instance is None:
            cls._instance = super(FormatService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize format service."""
        # Only initialize once
        if not FormatService._initialized:
            super().__init__(service_name="format")
            self._format_validators: Dict[str, Callable] = {}
            self._format_metadata: Dict[str, FormatMetadata] = {}
            self._register_default_validators()
            FormatService._initialized = True

    async def _start(self) -> None:
        """Start format service."""
        try:
            logger.info(
                "Format service started with {} validators",
                len(self._format_validators)
            )
        except Exception as e:
            raise ConfigurationError("Failed to start format service", {"error": str(e)})

    def register_format(
        self,
        format_type: str,
        validator: Callable,
        description: str,
        examples: List[str]
    ) -> None:
        """Register a new format validator."""
        try:
            if format_type in self._format_validators:
                raise ConfigurationError(
                    "Format already registered",
                    {"format": format_type}
                )
            
            self._format_validators[format_type] = validator
            self._format_metadata[format_type] = FormatMetadata(
                description=description,
                examples=examples
            )
            logger.debug("Registered format validator: {}", format_type)
            
        except Exception as e:
            raise ConfigurationError(
                "Failed to register format",
                {
                    "format": format_type,
                    "error": str(e)
                }
            )

    def validate_format(self, format_type: str, value: Any) -> Optional[str]:
        """Validate value against format type."""
        try:
            if format_type not in self._format_validators:
                raise ValidationError(
                    "Unknown format type",
                    {
                        "format": format_type,
                        "available_formats": list(self._format_validators.keys())
                    }
                )
                
            validator = self._format_validators[format_type]
            error = validator(value)
            
            if error:
                raise ValidationError(
                    "Format validation failed",
                    {
                        "format": format_type,
                        "value": str(value),
                        "error": error
                    }
                )
                
            return None
            
        except ValidationError:
            raise
        except Exception as e:
            logger.error("Unexpected format validation error: {}", e)
            raise ValidationError(
                "Format validation failed",
                {
                    "format": format_type,
                    "error": str(e)
                }
            )

    def _validate_12bit(self, value: Any) -> Optional[str]:
        """Validate 12-bit value (0-4095)."""
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num_value = float(value)
            if not 0 <= num_value <= 4095:
                return "Value must be between 0 and 4095"
        except ValueError:
            return "Invalid numeric value"
        except Exception as e:
            logger.error("Unexpected error in 12-bit validation: {}", e)
            return f"Validation failed: {str(e)}"
        return None

    def _validate_percentage(self, value: Any) -> Optional[str]:
        """Validate percentage value (0-100)."""
        try:
            if not isinstance(value, (int, float)):
                return "Value must be numeric"
            num_value = float(value)
            if not 0 <= num_value <= 100:
                return "Value must be between 0 and 100"
        except ValueError:
            return "Invalid numeric value"
        except Exception as e:
            logger.error("Unexpected error in percentage validation: {}", e)
            return f"Validation failed: {str(e)}"
        return None

    def _validate_ip_address(self, value: str) -> Optional[str]:
        """Validate IP address format."""
        if not isinstance(value, str):
            return "Value must be string"
            
        try:
            pattern = r"^(\d{1,3}\.){3}\d{1,3}$"
            if not re.match(pattern, value):
                return "Invalid IP address format"
                
            # Validate each octet
            octets = value.split(".")
            for octet in octets:
                octet_value = int(octet)
                if not 0 <= octet_value <= 255:
                    return "IP address octets must be between 0 and 255"
        except ValueError:
            return "Invalid IP address format - octets must be numbers"
        except Exception as e:
            logger.error("Unexpected error in IP validation: {}", e)
            return f"Validation failed: {str(e)}"
                
        return None

    def _validate_hostname(self, value: str) -> Optional[str]:
        """Validate hostname format."""
        if not isinstance(value, str):
            return "Value must be string"
            
        try:
            pattern = r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$"
            if not re.match(pattern, value):
                return "Invalid hostname format"
                
            if len(value) > 255:
                return "Hostname too long (max 255 characters)"
        except Exception as e:
            logger.error("Unexpected error in hostname validation: {}", e)
            return f"Validation failed: {str(e)}"
            
        return None

    def _validate_port(self, value: Any) -> Optional[str]:
        """Validate port number."""
        try:
            if not isinstance(value, int):
                return "Port must be integer"
            if not 1 <= value <= 65535:
                return "Port must be between 1 and 65535"
        except ValueError:
            return "Invalid port number format"
        except Exception as e:
            logger.error("Unexpected error in port validation: {}", e)
            return f"Validation failed: {str(e)}"
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
                return "Path too long (max 260 characters)"
                
            # Additional path validation
            if not path.is_absolute() and '..' in str(path):
                return "Relative paths cannot contain parent directory references (..)"
                
        except Exception as e:
            logger.error("Unexpected error in path validation: {}", e)
            return f"Invalid path format: {str(e)}"
            
        return None

    def _validate_tag_path(self, value: str) -> Optional[str]:
        """Validate tag path format (group.subgroup.tag)."""
        if not isinstance(value, str):
            return "Tag path must be string"
            
        try:
            # Basic format validation
            pattern = r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)*$"
            if not re.match(pattern, value):
                return "Invalid tag path format - must be dot-separated alphanumeric segments"
                
            # Length validation
            if len(value) > 255:
                return "Tag path too long (max 255 characters)"
                
            # Segment validation
            segments = value.split(".")
            if len(segments) < 1:
                return "Tag path must have at least one segment"
                
            for segment in segments:
                if len(segment) > 63:
                    return "Tag path segment too long (max 63 characters)"
                    
        except Exception as e:
            logger.error("Unexpected error in tag path validation: {}", e)
            return f"Invalid tag path format: {str(e)}"
            
        return None

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
            ["192.168.0.1", "10.0.0.1"]
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
            ["80", "443", "8080"]
        )
        
        self.register_format(
            "path",
            self._validate_path,
            "File system path",
            ["C:/path/to/file", "/usr/local/bin"]
        )
        
        self.register_format(
            "tag_path",
            self._validate_tag_path,
            "PLC tag path (group.subgroup.tag)",
            ["system.status", "motor.speed"]
        )
