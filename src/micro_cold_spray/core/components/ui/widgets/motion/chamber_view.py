"""Widget for visualizing chamber and motion system."""
from typing import Dict, Any, Optional, Tuple
import logging
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush
from PySide6.QtCore import Qt, QRectF, QPointF, QSize

from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget

logger = logging.getLogger(__name__)

class ChamberView(BaseWidget):
    """Displays chamber visualization with real-time position."""
    
    # Class constants
    MARGIN = 20  # Reduced margin to allow more space for drawing
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent: Optional[QWidget] = None
    ):
        super().__init__(
            widget_id="widget_motion_chamber",
            ui_manager=ui_manager,
            update_tags=[
                "motion.position",
                "motion.state",
                "hardware.stage",
                "hardware.nozzle"
            ],
            parent=parent
        )
        
        # Default dimensions until we get updates
        self._stage = {
            'x': 200.0,  # mm total travel
            'y': 200.0,  # mm total travel
            'z': 40.0    # mm total travel
        }
        
        self._substrate = {
            'total': {
                'width': 158.14,   # mm (full holder width)
                'height': 158.14   # mm (full holder height)
            },
            'sprayable': {
                'width': 141.0,    # mm (sprayable area)
                'height': 141.0    # mm (sprayable area)
            },
            'trough': {
                'width': 132.74,   # mm (trough width)
                'offset_y': 16.51, # mm (from bottom edge)
                'height': 25.40    # mm (trough section height)
            }
        }
        
        # Chamber dimensions (20" x 20" in mm)
        self.CHAMBER_SIZE = 508.0  # 20 inches in mm
        
        # Calculate stage offset to center in chamber
        self.STAGE_OFFSET_X = (self.CHAMBER_SIZE - self._stage['x']) / 2
        self.STAGE_OFFSET_Y = (self.CHAMBER_SIZE - self._stage['y']) / 2
        
        # Fixed dimensions (mm)
        self.NOZZLE_DIAMETER = 15.24  # 0.6 inches
        self.NOZZLE_CENTER_DOT = 2.0  # mm
        self.NOZZLE_OFFSET = 19.05    # 0.75 inches from center
        
        # Current position
        self._position = {'x': 0.0, 'y': 0.0, 'z': 0.0}
        self._scale_factor = 1.0
        
        # Set minimum size but allow expansion
        self.setMinimumSize(500, 500)
        
        logger.info("Chamber view initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager."""
        try:
            if "motion.position" in data:
                pos = data["motion.position"]
                self.update_position(
                    pos.get('x', 0.0),
                    pos.get('y', 0.0),
                    pos.get('z', 0.0)
                )
            elif "hardware.stage" in data:
                # Update stage dimensions if they change
                if 'dimensions' in data["hardware.stage"]:
                    self._stage = data["hardware.stage"]["dimensions"]
                    # Recalculate stage offsets
                    self.STAGE_OFFSET_X = (self.CHAMBER_SIZE - self._stage['x']) / 2
                    self.STAGE_OFFSET_Y = (self.CHAMBER_SIZE - self._stage['y']) / 2
                    self.update()
                    
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self._ui_manager.unregister_widget("chamber_view")
        except Exception as e:
            logger.error(f"Error during chamber view cleanup: {e}")

    def _update_scale(self) -> None:
        """Update drawing scale factor."""
        # Calculate scale to fit chamber in widget with margins
        available_width = self.width() - (2 * self.MARGIN)
        available_height = self.height() - (2 * self.MARGIN)
        
        # Use the smaller dimension to maintain aspect ratio
        self._scale_factor = min(
            available_width / self.CHAMBER_SIZE,
            available_height / self.CHAMBER_SIZE
        )

    def sizeHint(self) -> QSize:
        """Provide size hint for layout management."""
        return QSize(500, 500)

    def minimumSizeHint(self) -> QSize:
        """Provide minimum size hint for layout management."""
        return QSize(500, 500)

    def resizeEvent(self, event) -> None:
        """Handle resize events."""
        super().resizeEvent(event)
        self._update_scale()
        self.update()  # Trigger repaint with new size

    def _world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        """Convert world coordinates to screen coordinates.
        
        Returns integer screen coordinates for drawing functions.
        """
        # Add margins and scale
        screen_x = round(self.MARGIN + x * self._scale_factor)
        screen_y = round(self.MARGIN + y * self._scale_factor)
        return screen_x, screen_y

    def paintEvent(self, event):
        """Handle paint event."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Update scale factor
            self._update_scale()
            
            # Draw chamber outline
            self._draw_chamber(painter)
            
            # Draw stage limits
            self._draw_stage_limits(painter)
            
            # Draw build plate
            self._draw_build_plate(painter)
            
            # Draw nozzles
            self._draw_nozzles(painter)
            
            # Draw current position
            self._draw_position(painter)
            
        except Exception as e:
            logger.error(f"Error painting chamber view: {e}")

    def _draw_chamber(self, painter: QPainter) -> None:
        """Draw chamber outline."""
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)
        
        x1, y1 = self._world_to_screen(0, 0)
        x2, y2 = self._world_to_screen(self.CHAMBER_SIZE, self.CHAMBER_SIZE)
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def _draw_stage_limits(self, painter: QPainter) -> None:
        """Draw stage travel limits."""
        pen = QPen(QColor(100, 100, 100))  # Dark gray
        pen.setWidth(1)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        
        # Draw stage travel limits centered in chamber
        x1, y1, x2, y2 = self._get_stage_rect()
        painter.drawRect(int(x1), int(y1), int(x2 - x1), int(y2 - y1))

    def _draw_build_plate(self, painter: QPainter) -> None:
        """Draw build plate with sprayable area and trough."""
        # Position is relative to stage limits
        stage_pos_x = self.STAGE_OFFSET_X + self._position['x']
        stage_pos_y = self.STAGE_OFFSET_Y + self._position['y']
        
        # Draw total build plate outline
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)
        
        half_width = self._substrate['total']['width'] / 2
        half_height = self._substrate['total']['height'] / 2
        
        x1, y1 = self._world_to_screen(
            stage_pos_x - half_width,
            stage_pos_y - half_height
        )
        x2, y2 = self._world_to_screen(
            stage_pos_x + half_width,
            stage_pos_y + half_height
        )
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw sprayable area
        pen.setColor(QColor(0, 255, 0, 128))
        painter.setPen(pen)
        
        half_spray_width = self._substrate['sprayable']['width'] / 2
        half_spray_height = self._substrate['sprayable']['height'] / 2
        
        x1, y1 = self._world_to_screen(
            stage_pos_x - half_spray_width,
            stage_pos_y - half_spray_height
        )
        x2, y2 = self._world_to_screen(
            stage_pos_x + half_spray_width,
            stage_pos_y + half_spray_height
        )
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw trough extension (white outline)
        pen = QPen(Qt.GlobalColor.white)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Draw at top of stage (negative Y in screen coordinates)
        x1, y1 = self._world_to_screen(
            stage_pos_x - half_width,
            stage_pos_y - half_height - 25.4  # Extend above stage
        )
        x2, y2 = self._world_to_screen(
            stage_pos_x + half_width,
            stage_pos_y - half_height  # Connect to stage top
        )
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)
        
        # Draw actual trough area (blue)
        pen.setColor(QColor(0, 128, 255, 128))
        painter.setPen(pen)
        brush = QBrush(QColor(0, 128, 255, 64))
        painter.setBrush(brush)
        
        trough_width = self._substrate['trough']['width'] / 2
        x1, y1 = self._world_to_screen(
            stage_pos_x - trough_width,
            stage_pos_y - half_height - 25.4 + (25.4 - 16.51) / 2  # Center 16.51mm height in 25.4mm space
        )
        x2, y2 = self._world_to_screen(
            stage_pos_x + trough_width,
            stage_pos_y - half_height - 25.4 + (25.4 + 16.51) / 2
        )
        painter.drawRect(x1, y1, x2 - x1, y2 - y1)

    def _draw_nozzles(self, painter: QPainter) -> None:
        """Draw fixed nozzle positions."""
        pen = QPen(Qt.GlobalColor.yellow)
        pen.setWidth(2)
        painter.setPen(pen)
        brush = QBrush(QColor(255, 255, 0, 64))
        painter.setBrush(brush)
        
        # Position nozzles at exact chamber center
        chamber_center_x = self.CHAMBER_SIZE / 2
        chamber_center_y = self.CHAMBER_SIZE / 2
        
        radius = self.NOZZLE_DIAMETER / 2 * self._scale_factor
        
        # Draw both nozzles
        for x_offset in [-self.NOZZLE_OFFSET, self.NOZZLE_OFFSET]:
            x, y = self._world_to_screen(
                chamber_center_x + x_offset,
                chamber_center_y
            )
            # Draw outer circle
            painter.drawEllipse(QPointF(x, y), radius, radius)
            
            # Draw center dot
            center_radius = self.NOZZLE_CENTER_DOT / 2 * self._scale_factor
            pen.setWidth(1)
            painter.setPen(pen)
            brush = QBrush(Qt.GlobalColor.yellow)
            painter.setBrush(brush)
            painter.drawEllipse(QPointF(x, y), center_radius, center_radius)

    def _draw_position(self, painter: QPainter) -> None:
        """Draw current position marker."""
        if not all(v is not None for v in self._position.values()):
            return
            
        pen = QPen(Qt.GlobalColor.red)
        pen.setWidth(2)
        painter.setPen(pen)
        
        # Convert stage coordinates to chamber coordinates
        stage_pos_x = self.STAGE_OFFSET_X + self._position['x']
        stage_pos_y = self.STAGE_OFFSET_Y + self._position['y']
        
        # Convert to screen coordinates
        x, y = self._world_to_screen(stage_pos_x, stage_pos_y)
        
        # Draw crosshair
        size = 5
        painter.drawLine(x - size, y, x + size, y)
        painter.drawLine(x, y - size, x, y + size)

    def update_position(self, x: float, y: float, z: float) -> None:
        """Update current position."""
        self._position = {'x': x, 'y': y, 'z': z}
        self.update()  # Trigger repaint

    def _get_stage_rect(self) -> tuple[float, float, float, float]:
        """Get stage rectangle coordinates."""
        x1, y1 = self._world_to_screen(
            self.STAGE_OFFSET_X,
            self.STAGE_OFFSET_Y
        )
        x2, y2 = self._world_to_screen(
            self.STAGE_OFFSET_X + self._stage['x'],
            self.STAGE_OFFSET_Y + self._stage['y']
        )
        return x1, y1, x2, y2