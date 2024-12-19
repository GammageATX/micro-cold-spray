"""Unified configuration system using Dynaconf."""

from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from dynaconf import Dynaconf, Validator, ValidationError
from pydantic import PostgresDsn

# Get the project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.parent

# Initialize Dynaconf with both application settings and user configs
settings = Dynaconf(
    envvar_prefix="MICROCOLDSPRAY",
    settings_files=[
        # Application settings
        str(PROJECT_ROOT / "dynaconf.yaml"),  # Core settings
        str(PROJECT_ROOT / ".secrets.yaml"),  # Secrets
        str(PROJECT_ROOT / "settings.local.yaml"),  # Local overrides
        
        # User configurations - loaded as namespaces
        str(PROJECT_ROOT / "data/configs/process/*.yaml"),  # Process configs
        str(PROJECT_ROOT / "data/configs/hardware/*.yaml"),  # Hardware configs
        str(PROJECT_ROOT / "data/configs/patterns/*.yaml"),  # Pattern configs
        str(PROJECT_ROOT / "data/configs/materials/*.yaml"),  # Material configs
    ],
    environments=True,
    load_dotenv=True,
    merge_enabled=True,  # Merge nested dictionaries
    env_switcher="MICROCOLDSPRAY_ENV",
)

# Register core validators
settings.validators.register(
    # Database settings
    Validator("database.host", must_exist=True, is_type_of=str),
    Validator("database.port", must_exist=True, is_type_of=int),
    Validator("database.name", must_exist=True, is_type_of=str),
    Validator("database.user", must_exist=True, is_type_of=str),
    Validator("database.password", must_exist=True, is_type_of=str),
    
    # Process validation
    Validator("process.validation.chamber_pressure_max", must_exist=True, is_type_of=(int, float)),
    Validator("process.validation.min_feeder_flow", must_exist=True, is_type_of=(int, float)),
    
    # Hardware validation
    Validator("hardware.sets", must_exist=True, is_type_of=dict),
    
    # Gas validation
    Validator("gas.types", must_exist=True, is_type_of=list),
)


def get_database_url() -> PostgresDsn:
    """Generate the PostgreSQL connection URL from settings."""
    return PostgresDsn.build(
        scheme="postgresql",
        user=settings.database.user,
        password=settings.database.password,
        host=settings.database.host,
        port=settings.database.port,
        path=f"/{settings.database.name}",
    )


def get_config(config_type: str, name: str) -> Optional[Dict[str, Any]]:
    """Get a configuration by type and name.
    
    Args:
        config_type: Type of configuration (process, hardware, pattern, material)
        name: Name of the configuration
        
    Returns:
        Configuration data if found, None otherwise
    """
    try:
        return settings.get(f"{config_type}.{name}")
    except AttributeError:
        return None


def save_config(config_type: str, name: str, data: Dict[str, Any]) -> None:
    """Save a configuration.
    
    Args:
        config_type: Type of configuration
        name: Name of the configuration
        data: Configuration data to save
    """
    config_dir = PROJECT_ROOT / "data/configs" / config_type
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_file = config_dir / f"{name}.yaml"
    
    # Add metadata
    data["metadata"] = {
        "name": name,
        "type": config_type,
        "last_modified": datetime.utcnow().isoformat() + "Z",
    }
    
    # Write config
    settings.write(filename=str(config_file), data={name: data})
    
    # Force Dynaconf to reload configurations
    settings.reload()


def validate_config(config_type: str, data: Dict[str, Any]) -> bool:
    """Validate a configuration against its schema.
    
    Args:
        config_type: Type of configuration
        data: Configuration data to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Get validators for this config type
        validators = settings.validators.get(config_type, [])
        
        # Run validation
        for validator in validators:
            validator(settings, data)
        return True
        
    except ValidationError:
        return False


def list_configs(config_type: str) -> List[Dict[str, Any]]:
    """List all configurations of a specific type.
    
    Args:
        config_type: Type of configuration to list
        
    Returns:
        List of configuration metadata
    """
    try:
        configs = settings.get(config_type, {})
        return [
            {
                "name": name,
                "metadata": data.get("metadata", {})
            }
            for name, data in configs.items()
            if isinstance(data, dict)
        ]
    except AttributeError:
        return []


# Validate settings at startup
settings.validators.validate()
