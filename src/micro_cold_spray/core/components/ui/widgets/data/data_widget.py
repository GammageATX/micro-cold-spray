"""Widget for displaying and managing data collection."""
from datetime import datetime
from typing import Any, Dict

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
                "sequence.loaded",
                "sequence.state",
                "sequence.started",
                "sequence.completed",
                "data.collection.state",
                "data.list"
            ],
            parent=parent
        )

        self._current_sequence = None
        self._collection_active = False

        self._init_ui()
        logger.info("Data widget initialized")

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

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager."""
        try:
            logger.debug(f"DataWidget received update: {data}")

            if "data.list" in data:
                list_data = data["data.list"]
                if list_data.get("type") == "sequences":
                    # Update display when sequence list changes
                    self._update_display()
            elif "sequence.loaded" in data:
                # Get sequence info from the loaded data
                sequence_info = data.get("sequence.loaded", {})
                logger.debug(f"Processing sequence.loaded update: {sequence_info}")

                # Get user from parent window if available, with better fallback handling
                user = "DefaultUser"  # Default fallback
                try:
                    parent_window = self.window()
                    if hasattr(parent_window, 'connection_status'):
                        current_user = parent_window.connection_status.user_combo.currentText()
                        if current_user and current_user.strip():
                            user = current_user
                except Exception as e:
                    logger.warning(f"Could not get user from connection status: {e}")

                # Store sequence info for filename generation
                self._current_sequence = {
                    "name": sequence_info.get("name", "DefaultSequence"),
                    "user": user,
                    "metadata": sequence_info.get("metadata", {})
                }
                logger.debug(f"Updated current sequence: {self._current_sequence}")

                # Force display update
                self._update_display()
                self.status_label.setText("Status: Ready for data collection")

            elif "sequence.state" in data:
                state = data.get("sequence.state", {}).get("state", "")
                logger.debug(f"Processing sequence.state update: {state}")
                if state == "RUNNING":
                    self._collection_active = True
                    self.status_label.setText("Status: Collecting Data")
                elif state in ["COMPLETED", "CANCELLED", "ERROR"]:
                    self._collection_active = False
                    self.status_label.setText("Status: Collection Complete")
                self._update_display()

            elif "data.collection.state" in data:
                collection_state = data["data.collection.state"]
                await self._handle_collection_state(collection_state)

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self.send_update("system.error", f"Data widget error: {str(e)}")

    def _update_display(self) -> None:
        """Update the display with current information."""
        try:
            logger.debug(f"Updating display with current sequence: {self._current_sequence}")
            if self._current_sequence and self._current_sequence.get("name"):
                sequence_name = self._current_sequence["name"]
                user_name = self._current_sequence["user"]

                # Format: username_sequencename_YYYYMMDD_HHMMSS.csv
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{user_name}_{sequence_name}_{timestamp}.csv".replace(" ", "_")

                # Example: DefaultUser_TestSequence_20240125_143022.csv
                self.filename_label.setText(f"Output File: {filename}")
                logger.debug(f"Updated filename to: {filename}")
                logger.debug(
                    f"Using sequence info - Name: {sequence_name}, User: {user_name}")

                status = "Collecting" if self._collection_active else "Ready"
                self.status_label.setText(f"Status: {status}")
            else:
                logger.debug("No sequence info available for filename")
                logger.debug(
                    f"Current sequence data: {
                        self._current_sequence}")
                self.filename_label.setText("Output File: None")
                self.status_label.setText("Status: Idle")

        except Exception as e:
            logger.error(f"Error updating data widget display: {e}")

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
            await self.send_update("system.error", f"Error handling collection state: {str(e)}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up any resources
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
