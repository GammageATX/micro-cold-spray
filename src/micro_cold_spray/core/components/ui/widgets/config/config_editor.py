"""Configuration editor widget."""
from typing import Dict, Any
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTreeWidget,
    QTreeWidgetItem, QComboBox
)

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

class ConfigEditor(BaseWidget):
    """Widget for editing system configuration."""
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_config_editor",
            ui_manager=ui_manager,
            update_tags=[
                "config.current",
                "config.status",
                "config.validation"
            ],
            parent=parent
        )
        
        self._init_ui()
        logger.info("Config editor initialized")
    
    def _init_ui(self) -> None:
        """Initialize the config editor UI."""
        layout = QVBoxLayout()
        
        # Config file selection
        selection_layout = QHBoxLayout()
        self._file_combo = QComboBox()
        self._reload_btn = QPushButton("Reload")
        selection_layout.addWidget(QLabel("Config File:"))
        selection_layout.addWidget(self._file_combo)
        selection_layout.addWidget(self._reload_btn)
        layout.addLayout(selection_layout)
        
        # Config tree
        self._config_tree = QTreeWidget()
        self._config_tree.setHeaderLabels(["Setting", "Value"])
        self._config_tree.setColumnWidth(0, 200)  # Name column
        layout.addWidget(self._config_tree)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self._save_btn = QPushButton("Save Changes")
        self._reset_btn = QPushButton("Reset")
        control_layout.addWidget(self._save_btn)
        control_layout.addWidget(self._reset_btn)
        layout.addLayout(control_layout)
        
        self.setLayout(layout)
        
        # Connect signals
        self._reload_btn.clicked.connect(self._reload_config)
        self._save_btn.clicked.connect(self._save_changes)
        self._reset_btn.clicked.connect(self._reset_changes)
        self._file_combo.currentTextChanged.connect(self._load_config_file)
    
    async def _reload_config(self) -> None:
        """Reload current configuration."""
        try:
            await self._ui_manager.send_update("config/reload", {})
        except Exception as e:
            logger.error(f"Error reloading config: {e}")
    
    async def _save_changes(self) -> None:
        """Save configuration changes."""
        try:
            await self._ui_manager.send_update("config/save", {})
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    async def _reset_changes(self) -> None:
        """Reset configuration changes."""
        try:
            await self._ui_manager.send_update("config/reset", {})
        except Exception as e:
            logger.error(f"Error resetting config: {e}")
    
    async def _load_config_file(self, filename: str) -> None:
        """Load configuration file."""
        try:
            await self._ui_manager.send_update("config/load", {"filename": filename})
        except Exception as e:
            logger.error(f"Error loading config file: {e}")