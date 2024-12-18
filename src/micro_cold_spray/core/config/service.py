"""Core configuration service for managing user-editable settings."""

from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml

from dynaconf import Dynaconf
from pydantic import BaseModel, Field

from micro_cold_spray.infrastructure.config import settings as app_settings


class ConfigMetadata(BaseModel):
    """Metadata for a configuration entry."""
    name: str
    description: str
    version: str = Field(default="1.0.0")
    last_modified: Optional[str] = None


class ConfigData(BaseModel):
    """Configuration data with metadata."""
    metadata: ConfigMetadata
    data: Dict[str, Any]


class ConfigService:
    """Service for managing user-editable configurations."""
    
    def __init__(self):
        """Initialize the configuration service."""
        self.config_dir = Path(app_settings.core.config.directory)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Dynaconf for user configs
        self.settings = Dynaconf(
            settings_files=[str(self.config_dir / "*.yaml")],
            environments=False,
            load_dotenv=False,
        )
    
    def get_config(self, name: str) -> Optional[ConfigData]:
        """Get a configuration by name."""
        config_file = self.config_dir / f"{name}.yaml"
        if not config_file.exists():
            return None
            
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
            return ConfigData(**data)
    
    def list_configs(self) -> List[ConfigMetadata]:
        """List all available configurations."""
        configs = []
        for config_file in self.config_dir.glob("*.yaml"):
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
                configs.append(ConfigMetadata(**data["metadata"]))
        return configs
    
    def save_config(self, name: str, config: ConfigData) -> None:
        """Save a configuration."""
        config_file = self.config_dir / f"{name}.yaml"
        with open(config_file, 'w') as f:
            yaml.safe_dump(config.dict(), f)
    
    def delete_config(self, name: str) -> bool:
        """Delete a configuration."""
        config_file = self.config_dir / f"{name}.yaml"
        if not config_file.exists():
            return False
        config_file.unlink()
        return True
    
    def validate_config(self, config: ConfigData) -> bool:
        """Validate a configuration against its schema."""
        # TODO: Implement schema validation
        return True


# Singleton instance
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """Get the singleton config service instance."""
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service


def cleanup_config_service() -> None:
    """Cleanup the config service singleton."""
    global _config_service
    _config_service = None 