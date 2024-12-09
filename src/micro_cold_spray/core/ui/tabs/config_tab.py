"""Configuration tab for system settings."""
from typing import Any, Dict, Protocol, runtime_checkable, cast
import asyncio

from loguru import logger
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..managers.ui_update_manager import UIUpdateManager
from ..widgets.base_widget import BaseWidget
from ..widgets.config.config_editor import ConfigEditor


@runtime_checkable
class ConfigEditorProtocol(Protocol):
    """Protocol for config editor interface."""

    async def update_config(self, config: Dict[str, Any]) -> None:
        """Update editor configuration."""
        pass

    async def update_status(self, status: Dict[str, Any]) -> None:
        """Update editor status."""
        pass

    async def handle_connection_change(self, connected: bool) -> None:
        """Handle connection state change."""
        pass


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
                "config/current",
                "config/status",
                "config/backup",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        # Initialize status label first
        self._status_label = QLabel()
        self._status_label.setStyleSheet("color: gray; font-style: italic;")
        self._connected = False

        # Initialize widgets with protocol types
        self._config_editor = None
        self._backup_manager = None

        self._init_ui()
        logger.info("Config tab initialized")

    def _init_ui(self) -> None:
        """Initialize the config tab UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 5, 10, 10)

        # Add config editor
        editor = ConfigEditor(self._ui_manager)
        self._config_editor = cast(ConfigEditorProtocol, editor)
        layout.addWidget(cast(QWidget, editor))

        # Load available config files
        asyncio.create_task(self._load_config_files())

        self.setLayout(layout)

    def _update_status_label(self) -> None:
        """Update the status label based on connection state."""
        if self._connected:
            self._status_label.setText("Connected - Hardware configuration active")
        else:
            self._status_label.setText("Disconnected - Using local configuration")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "system/connection" in data:
                was_connected = self._connected
                self._connected = data.get("connected", False)
                if was_connected != self._connected:
                    self._update_status_label()
                    await self._notify_connection_state()

            if "config/current" in data:
                config_data = data.get("config/current", {})
                if self._config_editor is not None:
                    # In disconnected mode, use local config only
                    if not self._connected:
                        config_data = self._filter_hardware_config(config_data)
                    await self._config_editor.update_config(config_data)

            if "config/status" in data:
                status_data = data.get("config/status", {})
                if self._config_editor is not None:
                    await self._config_editor.update_status(status_data)

            if "config/backup" in data:
                backup_data = data.get("config/backup", {})
                if self._backup_manager is not None:
                    await self._backup_manager.update_backup_status(backup_data)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "config_tab",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _filter_hardware_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Filter hardware-specific config when in disconnected mode."""
        try:
            # Create a copy to avoid modifying original
            filtered = config.copy()

            # Remove or modify hardware-specific sections
            if "hardware" in filtered:
                hw_config = filtered["hardware"]

                # Keep motion limits and other simulation-relevant settings
                safe_keys = ["motion", "visualization", "simulation"]
                filtered["hardware"] = {
                    k: v for k, v in hw_config.items()
                    if k in safe_keys
                }

            return filtered

        except Exception as e:
            logger.error(f"Error filtering hardware config: {e}")
            return config

    async def _notify_connection_state(self) -> None:
        """Notify child widgets of connection state change."""
        try:
            widgets = [self._config_editor, self._backup_manager]

            for widget in widgets:
                if widget is not None and hasattr(widget, 'handle_connection_change'):
                    await widget.handle_connection_change(self._connected)

        except Exception as e:
            logger.error(f"Error notifying widgets of connection state: {e}")

    async def cleanup(self) -> None:
        """Clean up config tab and child widgets."""
        try:
            # Clean up child widgets first
            widgets = [self._config_editor, self._backup_manager]

            for widget in widgets:
                if widget is not None:
                    try:
                        await widget.cleanup()
                    except Exception as e:
                        logger.error(f"Error cleaning up widget: {e}")

            # Then clean up self
            await super().cleanup()

        except Exception as e:
            logger.error(f"Error during config tab cleanup: {e}")

    async def _load_config_files(self) -> None:
        """Load available config files from disk."""
        try:
            # Get config files from config manager
            await self._ui_manager.send_update(
                "config/request",
                {
                    "type": "list",
                    "source": "config_tab"
                }
            )

            logger.debug("Requested config file list")
        except Exception as e:
            logger.error(f"Error loading config files: {e}")
            await self._ui_manager.send_update(
                "error",
                {
                    "source": "config_tab",
                    "message": str(e),
                    "level": "error"
                }
            )
