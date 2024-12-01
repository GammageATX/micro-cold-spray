"""Widget for managing saved positions."""
import logging
from typing import Any, Dict
from PySide6.QtWidgets import (
    QHeaderView,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)


class PositionTable(BaseWidget):
    """Table for storing and managing motion positions."""

    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="widget_motion_positions",
            ui_manager=ui_manager,
            update_tags=["motion.position", "motion.error"],
            parent=parent
        )
        self._current_position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._stored_positions = []
        self._init_ui()
        logger.info("Position table initialized")

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout()

        # Add position button
        add_btn = QPushButton("Add Current Position")
        add_btn.clicked.connect(self._add_current_position)
        layout.addWidget(add_btn)

        # Position table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "X", "Y", "Z"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.setLayout(layout)

    def _add_current_position(self) -> None:
        """Add current position to table."""
        try:
            # Create position name
            name = f"P{len(self._stored_positions) + 1}"

            # Add to stored positions
            position = {
                'name': name,
                'x': self._current_position.get('x', 0.0),
                'y': self._current_position.get('y', 0.0),
                'z': self._current_position.get('z', 0.0)
            }
            self._stored_positions.append(position)

            # Add to table
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(name))
            self.table.setItem(
                row, 1, QTableWidgetItem(f"{position['x']:.3f}"))
            self.table.setItem(
                row, 2, QTableWidgetItem(f"{position['y']:.3f}"))
            self.table.setItem(
                row, 3, QTableWidgetItem(f"{position['z']:.3f}"))

            logger.debug(f"Added position {name}: {position}")

        except Exception as e:
            logger.error(f"Error adding position: {e}")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "motion.position" in data:
                self._current_position = data["motion.position"]

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await self._ui_manager.unregister_widget(self._widget_id)
        except Exception as e:
            logger.error(f"Error during position table cleanup: {e}")
