"""Configuration tab for system settings."""
from typing import Dict, Any
import logging
from PySide6.QtWidgets import QVBoxLayout

from ..widgets.base_widget import BaseWidget
from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.config.config_editor import ConfigEditor
from ..widgets.config.backup_manager import BackupManager

logger = logging.getLogger(__name__)

class ConfigTab(BaseWidget):
    """Tab for system configuration."""
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="tab_config",
            ui_manager=ui_manager,
            update_tags=[
                "config.current",
                "config.status",
                "config.backup"
            ],
            parent=parent
        )
        
        self._config_editor = None
        self._backup_manager = None
        
        self._init_ui()
        logger.info("Config tab initialized")

    def _init_ui(self) -> None:
        """Initialize the config tab UI."""
        layout = QVBoxLayout()
        
        # Add config editor
        self._config_editor = ConfigEditor(self._ui_manager)
        layout.addWidget(self._config_editor)
        
        # Add backup manager
        self._backup_manager = BackupManager(self._ui_manager)
        layout.addWidget(self._backup_manager)
        
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "config.current" in data:
                # Handle config updates
                pass
                
            if "config.status" in data:
                # Handle status updates
                pass
                
            if "config.backup" in data:
                # Handle backup updates
                pass
                
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def cleanup(self) -> None:
        """Clean up config tab and child widgets."""
        try:
            # Clean up child widgets first
            if hasattr(self, '_config_editor') and self._config_editor is not None:
                try:
                    await self._config_editor.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up config editor: {e}")
                    
            if hasattr(self, '_backup_manager') and self._backup_manager is not None:
                try:
                    await self._backup_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up backup manager: {e}")
                    
            # Then clean up self
            if hasattr(self, 'cleanup') and super().cleanup is not None:
                await super().cleanup()
                
        except Exception as e:
            logger.error(f"Error during config tab cleanup: {e}")
