"""Configuration backup management widget."""
from typing import Dict, Any, List
import logging
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget
)

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

class BackupManager(BaseWidget):
    """Widget for managing configuration backups."""
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_config_backup",
            ui_manager=ui_manager,
            update_tags=[
                "config.backup.list",
                "config.backup.status"
            ],
            parent=parent
        )
        
        self._init_ui()
        logger.info("Backup manager initialized")

    def _init_ui(self) -> None:
        """Initialize the backup manager UI."""
        layout = QVBoxLayout()
        
        # Backup list
        self._backup_list = QListWidget()
        layout.addWidget(QLabel("Available Backups:"))
        layout.addWidget(self._backup_list)
        
        # Control buttons
        control_layout = QHBoxLayout()
        self._create_btn = QPushButton("Create Backup")
        self._restore_btn = QPushButton("Restore Selected")
        self._delete_btn = QPushButton("Delete Selected")
        control_layout.addWidget(self._create_btn)
        control_layout.addWidget(self._restore_btn)
        control_layout.addWidget(self._delete_btn)
        layout.addLayout(control_layout)
        
        # Status label
        self._status_label = QLabel("Ready")
        layout.addWidget(self._status_label)
        
        self.setLayout(layout)
        
        # Connect signals
        self._create_btn.clicked.connect(self._create_backup)
        self._restore_btn.clicked.connect(self._restore_backup)
        self._delete_btn.clicked.connect(self._delete_backup)
        self._backup_list.itemSelectionChanged.connect(self._update_buttons)

    async def _create_backup(self) -> None:
        """Create new backup."""
        try:
            await self._ui_manager.send_update("config/backup/create", {})
        except Exception as e:
            logger.error(f"Error creating backup: {e}")

    async def _restore_backup(self) -> None:
        """Restore selected backup."""
        try:
            selected = self._backup_list.currentItem()
            if selected:
                await self._ui_manager.send_update(
                    "config/backup/restore",
                    {"backup": selected.text()}
                )
        except Exception as e:
            logger.error(f"Error restoring backup: {e}")

    async def _delete_backup(self) -> None:
        """Delete selected backup."""
        try:
            selected = self._backup_list.currentItem()
            if selected:
                await self._ui_manager.send_update(
                    "config/backup/delete",
                    {"backup": selected.text()}
                )
        except Exception as e:
            logger.error(f"Error deleting backup: {e}")

    def _update_buttons(self) -> None:
        """Update button states based on selection."""
        has_selection = self._backup_list.currentItem() is not None
        self._restore_btn.setEnabled(has_selection)
        self._delete_btn.setEnabled(has_selection)