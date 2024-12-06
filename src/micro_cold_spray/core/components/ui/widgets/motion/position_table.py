"""Position table widget for storing and managing positions."""
from typing import Any, Dict
import asyncio

from loguru import logger
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget


class PositionTable(BaseWidget):
    """Widget for storing and managing positions."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_motion_positions",
            ui_manager=ui_manager,
            update_tags=[
                "motion.position",
                "motion.state",
                "hardware.plc.connected"
            ],
            parent=parent
        )

        self._current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._is_connected = False
        self._init_ui()
        logger.info("Position table initialized")

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Create table
        self._table = QTableWidget()
        self._table.setColumnCount(4)  # Name, X, Y, Z
        self._table.setHorizontalHeaderLabels(["Name", "X", "Y", "Z"])

        # Set column widths
        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name column
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # X column
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)  # Y column
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Z column

        # Set fixed widths for coordinate columns
        self._table.setColumnWidth(1, 100)  # X column
        self._table.setColumnWidth(2, 100)  # Y column
        self._table.setColumnWidth(3, 100)  # Z column

        layout.addWidget(self._table)

        # Add control buttons
        button_layout = QHBoxLayout()

        self._add_btn = QPushButton("Add Current Position")
        self._remove_btn = QPushButton("Remove Selected")
        self._move_btn = QPushButton("Move to Selected")

        button_layout.addWidget(self._add_btn)
        button_layout.addWidget(self._remove_btn)
        button_layout.addWidget(self._move_btn)

        layout.addLayout(button_layout)

        # Connect signals with proper async handling
        self._add_btn.clicked.connect(self._add_current_position)
        self._remove_btn.clicked.connect(self._remove_selected)
        self._move_btn.clicked.connect(lambda: asyncio.create_task(self._move_to_selected()))

        self.setLayout(layout)

    async def update_position(self, position: Dict[str, float]) -> None:
        """Update current position.

        Args:
            position: Dictionary containing x, y, z coordinates
        """
        try:
            self._current_position = position.copy()
            logger.debug(f"Position table updated position: {position}")

            # Only update visualization in disconnected state
            # In connected state, let position feedback control visualization
            if not self._is_connected:
                await self._ui_manager.send_update(
                    "ui/update",
                    {
                        "type": "motion.position",
                        "data": {
                            "position": position,
                            "simulated": True,
                            "timestamp": None
                        }
                    }
                )
        except Exception as e:
            logger.error(f"Error updating position table: {e}")

    def _add_current_position(self) -> None:
        """Add current position to table."""
        try:
            # Get next available position name
            row_count = self._table.rowCount()
            position_name = f"Position {row_count + 1}"

            # Add new row
            self._table.insertRow(row_count)

            # Add position data
            x_pos = f"{self._current_position['x']:.3f}"
            y_pos = f"{self._current_position['y']:.3f}"
            z_pos = f"{self._current_position['z']:.3f}"

            self._table.setItem(row_count, 0, QTableWidgetItem(position_name))
            self._table.setItem(row_count, 1, QTableWidgetItem(x_pos))
            self._table.setItem(row_count, 2, QTableWidgetItem(y_pos))
            self._table.setItem(row_count, 3, QTableWidgetItem(z_pos))

            logger.debug(f"Added position to table: {self._current_position}")
        except Exception as e:
            logger.error(f"Error adding position to table: {e}")

    def _remove_selected(self) -> None:
        """Remove selected position from table."""
        try:
            selected = self._table.selectedItems()
            if not selected:
                return

            # Get unique rows (items come in column order)
            rows = set()
            for item in selected:
                rows.add(item.row())

            # Remove rows in reverse order to maintain indices
            for row in sorted(rows, reverse=True):
                self._table.removeRow(row)

            logger.debug(f"Removed rows: {rows}")
        except Exception as e:
            logger.error(f"Error removing positions: {e}")

    async def _move_to_selected(self) -> None:
        """Move to selected position."""
        try:
            selected = self._table.selectedItems()
            if not selected:
                return

            # Get row of first selected item
            row = selected[0].row()

            # Get position from table
            position = {
                'x': float(self._table.item(row, 1).text()),
                'y': float(self._table.item(row, 2).text()),
                'z': float(self._table.item(row, 3).text())
            }

            if self._is_connected:
                # In connected state, send move command
                await self._ui_manager.send_update(
                    "ui/update",
                    {
                        "type": "motion.position",
                        "data": {
                            "position": position,
                            "speed": 10.0,  # Default speed
                            "simulated": False,
                            "timestamp": None
                        }
                    }
                )
                logger.debug(f"Sent move command to position: {position}")
            else:
                # In disconnected state, send visualization update
                await self._ui_manager.send_update(
                    "ui/update",
                    {
                        "type": "motion.position",
                        "data": {
                            "position": position,
                            "simulated": True,
                            "timestamp": None
                        }
                    }
                )
                logger.debug(f"Sent visualization update to position: {position}")

        except Exception as e:
            logger.error(f"Error moving to position: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "motion.position" in data:
                position_data = data.get("motion.position", {})
                if isinstance(position_data, dict):
                    if "data" in position_data and "position" in position_data["data"]:
                        await self.update_position(position_data["data"]["position"])
                    elif "position" in position_data:
                        await self.update_position(position_data["position"])
                    else:
                        await self.update_position(position_data)

            elif "hardware.plc.connected" in data:
                self._is_connected = data.get("hardware.plc.connected", False)
                logger.debug(f"PLC connection state changed: {self._is_connected}")
                # Call Qt's update() without parameters
                self.update()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during position table cleanup: {e}")
