from pathlib import Path
import shutil
import yaml
from datetime import datetime
from typing import Optional
import aiofiles
import os


class ConfigFileService:
    def __init__(self, config_dir: Path, backup_dir: Optional[Path] = None):
        self.config_dir = Path(config_dir)
        self.backup_dir = backup_dir or self.config_dir / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def backup_config(self, config_type: str) -> bool:
        """Create a backup of the configuration file.
        
        Args:
            config_type: Type of configuration to backup
            
        Returns:
            bool: True if backup was successful
        """
        try:
            # Get source file path
            source_file = self.config_dir / f"{config_type}.yaml"
            if not source_file.exists():
                return False

            # Create timestamped backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"{config_type}_{timestamp}.yaml"

            # Use shutil for atomic copy operation
            shutil.copy2(source_file, backup_file)

            # Verify backup was created successfully
            if not backup_file.exists():
                return False

            # Verify file contents match
            with source_file.open('rb') as sf, backup_file.open('rb') as bf:
                if sf.read() != bf.read():
                    backup_file.unlink()  # Delete failed backup
                    return False

            return True

        except (OSError, IOError) as e:
            self.logger.error(f"Backup failed for {config_type}: {str(e)}")
            return False

    async def save_config(self, config_type: str, data: dict, backup: bool = True) -> bool:
        """Save configuration data to file with optional backup.
        
        Args:
            config_type: Type of configuration to save
            data: Configuration data to save
            backup: Whether to create backup before saving
            
        Returns:
            bool: True if save was successful
        """
        try:
            # Create backup first if requested
            if backup:
                backup_success = await self.backup_config(config_type)
                if not backup_success:
                    self.logger.error(f"Backup failed for {config_type}, aborting save")
                    return False

            # Save to temporary file first
            config_file = self.config_dir / f"{config_type}.yaml"
            temp_file = config_file.with_suffix('.yaml.tmp')
            
            async with aiofiles.open(temp_file, 'w') as f:
                yaml_content = yaml.dump(data, default_flow_style=False)
                await f.write(yaml_content)

            # Verify temp file was written correctly
            if not temp_file.exists():
                return False

            # Atomic rename of temp file to final file
            os.replace(temp_file, config_file)
            
            return True

        except Exception as e:
            self.logger.error(f"Save failed for {config_type}: {str(e)}")
            if temp_file.exists():
                temp_file.unlink()
            return False
