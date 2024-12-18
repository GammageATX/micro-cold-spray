"""Configuration repository implementation."""

from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import shutil
import yaml
from fastapi import HTTPException, status

from loguru import logger

from micro_cold_spray.core.config.models import ConfigData, ConfigMetadata


class ConfigRepository:
    """Repository for configuration data storage and versioning."""

    def __init__(self, config_dir: Path, backup_dir: Optional[Path] = None):
        """Initialize repository.
        
        Args:
            config_dir: Directory for configuration files
            backup_dir: Directory for backups (defaults to config_dir/backups)
        """
        self._config_dir = config_dir
        self._backup_dir = backup_dir or config_dir / "backups"
        self._initialize_directories()

    def _initialize_directories(self) -> None:
        """Create necessary directories."""
        try:
            self._config_dir.mkdir(parents=True, exist_ok=True)
            self._backup_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create directories: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to initialize config repository: {str(e)}"
            )

    def _get_config_path(self, config_type: str) -> Path:
        """Get path for a config file."""
        return self._config_dir / f"{config_type}.yaml"

    def _get_backup_path(self, config_type: str) -> Path:
        """Get path for a backup file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return self._backup_dir / f"{config_type}_{timestamp}.bak"

    async def load_config(self, config_type: str) -> ConfigData:
        """Load configuration from file.
        
        Args:
            config_type: Type of configuration to load
            
        Returns:
            Loaded configuration data
            
        Raises:
            HTTPException: If loading fails
        """
        config_path = self._get_config_path(config_type)
        
        if not config_path.exists():
            logger.error(f"Required config file not found: {config_type}.yaml")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Required config file not found: {config_type}.yaml"
            )
            
        try:
            with open(config_path, 'r') as f:
                data = yaml.safe_load(f)
                
            if not data:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Config file is empty: {config_type}.yaml"
                )

            # Get version from root level or inside config section
            version = data.get("version")
            if not version:
                # Try to get version from inside config section
                config_section = data.get(config_type, {})
                if isinstance(config_section, dict):
                    version = config_section.get("version")
                
                # Try to get version from info section if it exists
                if not version and isinstance(config_section, dict):
                    info = config_section.get("info", {})
                    if isinstance(info, dict):
                        version = info.get("version")

            if not version:
                logger.error(f"Version not found in config file: {config_type}.yaml")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Version not found in config file: {config_type}.yaml"
                )

            # Get the main config section
            config_data = data.get(config_type)
            if not config_data:
                logger.error(f"Config section '{config_type}' not found in {config_type}.yaml")
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Config section '{config_type}' not found in {config_type}.yaml"
                )

            metadata = ConfigMetadata(
                config_type=config_type,
                last_modified=datetime.fromtimestamp(config_path.stat().st_mtime),
                version=version
            )
            
            return ConfigData(metadata=metadata, data=config_data)
            
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML format in {config_type}.yaml: {e}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid YAML format in {config_type}.yaml: {str(e)}"
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to load config {config_type}.yaml: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to load config {config_type}.yaml: {str(e)}"
            )

    async def save_config(
        self,
        config_type: str,
        data: Dict[str, Any],
        create_backup: bool = False
    ) -> None:
        """Save configuration to file.
        
        Args:
            config_type: Type of configuration to save
            data: Configuration data to save
            create_backup: Whether to create a backup first
            
        Raises:
            HTTPException: If saving fails
        """
        config_path = self._get_config_path(config_type)
        
        try:
            # Create backup if requested
            if create_backup and config_path.exists():
                await self.create_backup(config_type)
            
            # Create config directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write config file
            with open(config_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
                
        except yaml.YAMLError as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to serialize config: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save config: {str(e)}"
            )

    async def create_backup(self, config_type: str) -> None:
        """Create a backup of the config file.
        
        Args:
            config_type: Type of configuration to backup
            
        Raises:
            HTTPException: If backup fails
        """
        source_path = self._get_config_path(config_type)
        backup_path = self._get_backup_path(config_type)
        
        if not source_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Config file not found: {config_type}"
            )
            
        try:
            self._backup_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, backup_path)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create backup: {str(e)}"
            )

    async def list_backups(self, config_type: str) -> List[Path]:
        """List available backups for a config type.
        
        Args:
            config_type: Type of configuration to list backups for
            
        Returns:
            List of backup file paths
        """
        try:
            pattern = f"{config_type}_*.bak"
            return sorted(
                self._backup_dir.glob(pattern),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to list backups: {str(e)}"
            )

    async def restore_backup(self, backup_path: Path) -> None:
        """Restore a configuration from backup.
        
        Args:
            backup_path: Path to backup file to restore
            
        Raises:
            HTTPException: If restore fails
        """
        if not backup_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup file not found: {backup_path}"
            )
            
        try:
            # Extract config type from backup filename
            config_type = backup_path.stem.split("_")[0]
            config_path = self._get_config_path(config_type)
            
            # Create backup of current config
            if config_path.exists():
                await self.create_backup(config_type)
            
            # Restore from backup
            shutil.copy2(backup_path, config_path)
            
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to restore backup: {str(e)}"
            )

    async def delete_backup(self, backup_path: Path) -> None:
        """Delete a backup file.
        
        Args:
            backup_path: Path to backup file to delete
            
        Raises:
            HTTPException: If deletion fails
        """
        if not backup_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup file not found: {backup_path}"
            )
            
        try:
            backup_path.unlink()
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete backup: {str(e)}"
            )
