"""Configuration editor widget."""
import logging
import asyncio
from typing import Any, Dict, Optional
import yaml

from PySide6.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPushButton,
    QTextEdit,
    QMessageBox,
)

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class ConfigEditor(BaseWidget):
    """Widget for editing system configuration files."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_config_editor",
            ui_manager=ui_manager,
            update_tags=[
                "config/current",
                "config/list",
                "config/update",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._current_config: Optional[Dict[str, Any]] = None
        self._init_ui()
        logger.info("Config editor initialized")

    def _init_ui(self) -> None:
        """Initialize the editor UI."""
        layout = QVBoxLayout()

        # File selection controls
        file_layout = QHBoxLayout()
        self._file_combo = QComboBox()
        self._file_combo.currentTextChanged.connect(self._on_file_selected)
        
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._on_save_clicked)
        self._save_btn.setEnabled(False)

        file_layout.addWidget(self._file_combo)
        file_layout.addWidget(self._save_btn)
        layout.addLayout(file_layout)

        # Config editor
        self._editor = QTextEdit()
        self._editor.textChanged.connect(self._on_text_changed)
        layout.addWidget(self._editor)

        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "config/current" in data:
                config_data = data["config/current"]
                if isinstance(config_data, dict):
                    self._current_config = config_data
                    self._update_editor()

            elif "config/list" in data:
                file_list = data["config/list"]
                if isinstance(file_list, list):
                    self._file_combo.clear()
                    self._file_combo.addItems(file_list)

            elif "system/connection" in data:
                connected = data.get("connected", False)
                self._update_button_states(connected)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_button_states(self, connected: bool) -> None:
        """Update button enabled states based on connection status."""
        try:
            self._save_btn.setEnabled(connected and bool(self._current_config))
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _update_editor(self) -> None:
        """Update editor with current config."""
        try:
            if self._current_config:
                yaml_text = yaml.dump(
                    self._current_config,
                    default_flow_style=False,
                    sort_keys=False
                )
                self._editor.setPlainText(yaml_text)
            else:
                self._editor.clear()
        except Exception as e:
            logger.error(f"Error updating editor: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _on_file_selected(self, filename: str) -> None:
        """Handle file selection change."""
        try:
            if filename:
                await self._ui_manager.send_update(
                    "config/request",
                    {
                        "name": filename
                    }
                )
        except Exception as e:
            logger.error(f"Error loading config file: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _on_text_changed(self) -> None:
        """Handle editor text changes."""
        try:
            # Enable save button if there are changes
            if self._current_config:
                self._save_btn.setEnabled(True)
        except Exception as e:
            logger.error(f"Error handling text change: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _on_save_clicked(self) -> None:
        """Handle save button click."""
        try:
            # Parse YAML text
            yaml_text = self._editor.toPlainText()
            config_data = yaml.safe_load(yaml_text)

            # Send update
            await self._ui_manager.send_update(
                "config/save",
                {
                    "name": self._file_combo.currentText(),
                    "data": config_data
                }
            )

            self._save_btn.setEnabled(False)

        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML format: {e}")
            QMessageBox.critical(
                self,
                "Save Error",
                f"Invalid YAML format: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during config editor cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_editor",
                    "message": str(e),
                    "level": "error"
                }
            )
