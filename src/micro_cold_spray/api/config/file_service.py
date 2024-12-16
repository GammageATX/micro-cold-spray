from pathlib import Path
import shutil
import yaml
from datetime import datetime
from typing import Optional, Dict, Any
import aiofiles
import os
import logging
from micro_cold_spray.api.base.exceptions import ConfigurationError


class ConfigFileService:
    def __init__(self, config_dir: Path, backup_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir)
        self._backup_dir = backup_dir or self.config_dir / "backups"
        self._backup_dir.mkdir(parents=True, exist_ok=True)
        self.backup_enabled = True
        self.logger = logging.getLogger(__name__)

    async def create_backup(self, config_path: Path) -> Path:
        """Create a backup of a config file.
        
        Args:
            config_path: Path to the config file to backup
            
        Returns:
            Path: Path to the created backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_path = self._backup_dir / f"{config_path.stem}_{timestamp}.bak"
        shutil.copy2(config_path, backup_path)
        return backup_path

    async def exists(self, config_name: str) -> bool:
        """Check if a config file exists.
        
        Args:
            config_name: Name of the config file
            
        Returns:
            bool: True if file exists
        """
        config_path = self.config_dir / config_name
        return config_path.exists()

    async def load_config(self, config_name: str) -> Dict[str, Any]:
        """Load a config file.
        
        Args:
            config_name: Name of the config file
            
        Returns:
            dict: Loaded config data
            
        Raises:
            ConfigurationError: If config file is invalid
        """
        config_path = self.config_dir / config_name
        try:
            async with aiofiles.open(config_path, 'r') as f:
                content = await f.read()
                return yaml.safe_load(content)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML in config file {config_name}: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"Error loading config file {config_name}: {str(e)}")

    async def save_config(self, config_name: str, data: Dict[str, Any]) -> bool:
        """Save configuration data to file with optional backup.
        
        Args:
            config_name: Name of the config file
            data: Configuration data to save
            
        Returns:
            bool: True if save was successful
        """
        try:
            config_path = self.config_dir / config_name
            
            # Create backup if enabled and file exists
            if self.backup_enabled and config_path.exists():
                await self.create_backup(config_path)

            # Save to temporary file first
            temp_file = config_path.with_suffix('.yaml.tmp')
            
            async with aiofiles.open(temp_file, 'w') as f:
                yaml_content = yaml.dump(data, default_flow_style=False)
                await f.write(yaml_content)

            # Atomic rename of temp file to final file
            os.replace(temp_file, config_path)
            
            return True

        except Exception as e:
            self.logger.error(f"Save failed for {config_name}: {str(e)}")
            if temp_file.exists():
                temp_file.unlink()
            return False
