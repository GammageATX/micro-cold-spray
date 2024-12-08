"""Widget for displaying and managing data collection."""
from datetime import datetime
from typing import Any, Dict
import asyncio

from loguru import logger
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget


class DataWidget(BaseWidget):
    """Widget showing data collection status and file information."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_dashboard_data",
            ui_manager=ui_manager,
            update_tags=[
                "sequence/loaded",
                "sequence/state",
                "data/collection/state",
                "data/files",
                "config/update",
                "system/error"
            ],
            parent=parent
        )

        self._current_sequence = None
        self._collection_active = False
        self._current_user = "Default User"

        self._init_ui()
        logger.info("Data widget initialized")

        # Load initial state
        asyncio.create_task(self._load_initial_state())

    def _init_ui(self):
        """Initialize the data widget UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)

        # Create frame with standard style
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.Box)
        frame.setFrameShadow(QFrame.Shadow.Plain)
        frame_layout = QVBoxLayout()

        # Add title
        title = QLabel("Data Collection")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        frame_layout.addWidget(title)

        # Collection status
        self.status_label = QLabel("Status: Idle")
        frame_layout.addWidget(self.status_label)

        # File information
        self.filename_label = QLabel("Output File: None")
        frame_layout.addWidget(self.filename_label)

        # Set frame layout
        frame.setLayout(frame_layout)
        layout.addWidget(frame)

        # Add stretch to keep widget compact
        layout.addStretch()

        self.setLayout(layout)

    async def _load_initial_state(self) -> None:
        """Load initial state from config."""
        try:
            # Get initial config directly
            config = await self.config_manager.get_config("application")
            env_config = config.get("application", {}).get("environment", {})

            # Get current user
            self._current_user = env_config.get("user", "Default User")

            # Subscribe to config updates for real-time changes
            await self._ui_manager._message_broker.subscribe(
                "config/update/application",
                self._handle_config_update
            )

        except Exception as e:
            logger.error(f"Error loading initial state: {e}")

    async def _handle_config_update(self, data: Dict[str, Any]) -> None:
        """Handle real-time config updates."""
        try:
            if "application" in data.get("data", {}):
                env_config = data["data"]["application"].get("environment", {})
                # Update current user if changed
                new_user = env_config.get("user", "Default User")
                if new_user != self._current_user:
                    self._current_user = new_user
                    # Update display if we have a sequence loaded
                    if self._current_sequence:
                        self._update_display()

        except Exception as e:
            logger.error(f"Error handling config update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "data_widget",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager."""
        try:
            if "sequence/loaded" in data:
                sequence_data = data["sequence/loaded"]
                logger.debug(f"Processing sequence/loaded update: {sequence_data}")

                if sequence_info := sequence_data.get("sequence", {}):
                    self._current_sequence = {
                        "name": sequence_info.get("name", "DefaultSequence"),
                        "user": self._current_user,
                        "metadata": sequence_info.get("metadata", {})
                    }
                    logger.debug(f"Updated current sequence: {self._current_sequence}")
                    self._update_display()
                    self.status_label.setText("Status: Ready for data collection")

            elif "sequence/state" in data:
                state = data.get("sequence/state", {}).get("state", "")
                logger.debug(f"Processing sequence/state update: {state}")
                if state == "RUNNING":
                    self._collection_active = True
                    self.status_label.setText("Status: Collecting Data")
                elif state in ["COMPLETED", "CANCELLED", "ERROR"]:
                    self._collection_active = False
                    self.status_label.setText("Status: Collection Complete")
                self._update_display()

            elif "data/collection/state" in data:
                collection_state = data["data/collection/state"]
                logger.debug(f"Processing data/collection/state update: {collection_state}")
                await self._handle_collection_state(collection_state)

            elif "data/files" in data:
                list_data = data["data/files"]
                logger.debug(f"Processing data/files update: {list_data}")
                if list_data.get("type") == "sequences":
                    self._update_display()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "data_widget",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_display(self) -> None:
        """Update the display with current information."""
        try:
            logger.debug(f"Updating display with current sequence: {self._current_sequence}")
            logger.debug(f"Current user: {self._current_user}")
            if self._current_sequence and self._current_sequence.get("name"):
                sequence_name = self._current_sequence["name"]
                user_name = self._current_sequence["user"]
                logger.debug(f"Generating filename with sequence: {sequence_name}, user: {user_name}")

                # Format: username_sequencename_YYYYMMDD_HHMMSS.csv
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{user_name}_{sequence_name}_{timestamp}.csv".replace(" ", "_")

                # Example: DefaultUser_TestSequence_20240125_143022.csv
                self.filename_label.setText(f"Output File: {filename}")
                logger.debug(f"Updated filename to: {filename}")
                logger.debug(f"Using sequence info - Name: {sequence_name}, User: {user_name}")

                status = "Collecting" if self._collection_active else "Ready"
                self.status_label.setText(f"Status: {status}")
            else:
                logger.debug("No sequence info available for filename")
                logger.debug(f"Current sequence data: {self._current_sequence}")
                self.filename_label.setText("Output File: None")
                self.status_label.setText("Status: Idle")

        except Exception as e:
            logger.error(f"Error updating data widget display: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "data_widget",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _handle_collection_state(self, state: Dict[str, Any]) -> None:
        """Handle data collection state updates."""
        try:
            logger.debug(f"Handling collection state update: {state}")
            collection_status = state.get("state", "")
            if collection_status == "COLLECTING":
                self._collection_active = True
                self.status_label.setText("Status: Collecting Data")
            elif collection_status == "STOPPED":
                self._collection_active = False
                self.status_label.setText("Status: Collection Complete")
            self._update_display()

        except Exception as e:
            logger.error(f"Error handling collection state: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "data_widget",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up any resources
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
