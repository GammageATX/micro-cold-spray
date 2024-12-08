"""Hardware tag monitoring widget."""
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import asyncio

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class TagMonitor(BaseWidget):
    """Real-time tag value monitoring widget."""

    # Define tag types as constants
    TAG_TYPES = ["STATUS", "CONTROL", "SENSOR", "CONFIG", "ALL"]

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_diagnostics_monitor",
            ui_manager=ui_manager,
            update_tags=[
                "tag/update",
                "tag/list",
                "tag/request",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        # Track tag values and history
        self._tag_values: Dict[str, Any] = {}
        self._tag_history: Dict[str, List[Tuple[datetime, Any]]] = {}
        self._history_length = 100  # Keep last 100 values

        # Current filter settings
        self._filter_text = ""
        self._filter_type: Optional[str] = None

        self._init_ui()
        self._start_timer()
        logger.info("Tag monitor initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "tag/update" in data:
                tag_data = data["tag/update"]
                await self._handle_tag_update(tag_data)

            elif "tag/list" in data:
                tag_list = data["tag/list"]
                self._update_tag_list(tag_list)

            elif "system/connection" in data:
                connected = data.get("connected", False)
                if not connected:
                    self._tag_values.clear()
                    self._tag_history.clear()
                    self._update_display()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _init_ui(self) -> None:
        """Setup tag monitor UI."""
        layout = QVBoxLayout()

        # Filter controls
        filter_group = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filter_group)

        # Search filter
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tags...")
        self.search_input.textChanged.connect(self._on_filter_changed)

        # Type filter
        self.type_combo = QComboBox()
        self.type_combo.addItem("All Types", None)
        for tag_type in self.TAG_TYPES:
            self.type_combo.addItem(tag_type, tag_type)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input)
        filter_layout.addWidget(QLabel("Type:"))
        filter_layout.addWidget(self.type_combo)
        layout.addWidget(filter_group)

        # Tag table
        self.tag_table = QTableWidget(0, 4)  # rows will be added dynamically
        self.tag_table.setHorizontalHeaderLabels([
            "Tag Name", "Value", "Last Update", "Type"
        ])

        # Set column stretching
        header = self.tag_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Tag name stretches
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.tag_table)

        # Status bar
        self.status_label = QLabel("Monitoring 0 tags")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _start_timer(self) -> None:
        """Start update timer."""
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_display)
        self._timer.start(1000)  # Update every second

    def _on_filter_changed(self, text: str) -> None:
        """Handle search filter change."""
        try:
            self._filter_text = text.lower()
            self._update_display()
        except Exception as e:
            logger.error(f"Error updating filter: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _on_type_changed(self, index: int) -> None:
        """Handle type filter change."""
        try:
            self._filter_type = self.type_combo.currentData()
            self._update_display()
        except Exception as e:
            logger.error(f"Error updating type filter: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _should_show_tag(self, tag_name: str, tag_type: str) -> bool:
        """Check if tag should be shown with current filters."""
        # Check text filter
        if self._filter_text and self._filter_text not in tag_name.lower():
            return False

        # Check type filter
        if self._filter_type and self._filter_type != "ALL" and tag_type != self._filter_type:
            return False

        return True

    def _update_display(self) -> None:
        """Update tag table display."""
        try:
            # Get current tags with proper tuple structure
            visible_tags = [
                # Return tuple of (name, (value, type))
                (name, self._tag_values[name])
                for name in self._tag_values
                # Use type from tuple
                if self._should_show_tag(name, self._tag_values[name][1])
            ]

            # Update table
            self.tag_table.setRowCount(len(visible_tags))
            for row, (name, (value, tag_type)) in enumerate(visible_tags):
                # Tag name
                self.tag_table.setItem(row, 0, QTableWidgetItem(name))

                # Value
                value_str = str(value) if value is not None else "None"
                self.tag_table.setItem(row, 1, QTableWidgetItem(value_str))

                # Last update
                last_update = self._tag_history[name][-1][0] if self._tag_history[name] else datetime.now()
                update_str = last_update.strftime("%H:%M:%S")
                self.tag_table.setItem(row, 2, QTableWidgetItem(update_str))

                # Type
                self.tag_table.setItem(row, 3, QTableWidgetItem(tag_type))

            # Update status
            total_tags = len(self._tag_values)
            visible_tags = self.tag_table.rowCount()
            self.status_label.setText(
                f"Showing {visible_tags} of {total_tags} tags"
            )

        except Exception as e:
            logger.error(f"Error updating display: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle tag value updates."""
        try:
            tag_name = data["tag"]
            new_value = data["value"]
            tag_type = data.get("type", "STATUS")  # Default to STATUS type

            # Update current value
            self._tag_values[tag_name] = (new_value, tag_type)

            # Update history
            if tag_name not in self._tag_history:
                self._tag_history[tag_name] = []

            self._tag_history[tag_name].append((datetime.now(), new_value))

            # Trim history if needed
            if len(self._tag_history[tag_name]) > self._history_length:
                self._tag_history[tag_name].pop(0)

        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            )

    def _update_tag_list(self, tag_list: List[str]) -> None:
        """Update list of available tags."""
        try:
            # Add any new tags
            for tag in tag_list:
                if tag not in self._tag_values:
                    self._tag_values[tag] = (None, "STATUS")
                    self._tag_history[tag] = []

            # Remove any deleted tags
            for tag in list(self._tag_values.keys()):
                if tag not in tag_list:
                    del self._tag_values[tag]
                    del self._tag_history[tag]

            self._update_display()

        except Exception as e:
            logger.error(f"Error updating tag list: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            ))

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, '_timer'):
                self._timer.stop()
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "tag_monitor",
                    "message": str(e),
                    "level": "error"
                }
            )
