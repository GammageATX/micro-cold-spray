"""Visualizes the spray sequence path on a 2D representation of the stage."""
import logging
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget
from .....infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)


class SequenceVisualizer(BaseWidget):
    """2D visualization of spray sequence paths."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_sequence_visualizer",
            ui_manager=ui_manager,
            update_tags=[
                "hardware.stage",
                "hardware.substrate",
                "sequence.path",
                "sequence.active_step"
            ],
            parent=parent
        )

        self._message_broker = message_broker

        # Initialize with default values
        self._stage = {'x': 200.0, 'y': 200.0}  # Default stage size
        self._substrate = {
            'sprayable': {'width': 141.0, 'height': 141.0}
        }  # Default substrate size

        # Store sequence path data
        # List of {start, end, type} dicts
        self._path_segments: List[Dict[str, Any]] = []
        self._active_step: Optional[int] = None

        # Set white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(palette)

        self.setMinimumSize(400, 400)
        logger.info("Sequence visualizer initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "hardware.stage" in data:
                self._stage = data["hardware.stage"]
                self.update()

            if "hardware.substrate" in data:
                self._substrate = data["hardware.substrate"]
                self.update()

            if "sequence.path" in data:
                self._path_segments = self._process_sequence(
                    data["sequence.path"])
                self.update()

            if "sequence.active_step" in data:
                self._active_step = data["sequence.active_step"]
                self.update()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _process_sequence(
            self, sequence_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process sequence data into drawable path segments."""
        segments = []
        current_pos = QPointF(0, 0)  # Start at origin

        try:
            for item in sequence_data:
                if item['type'] == 'pattern':
                    # Process pattern path points
                    pattern_segments = self._process_pattern(
                        item['pattern'], current_pos)
                    segments.extend(pattern_segments)
                    if pattern_segments:
                        current_pos = pattern_segments[-1]['end']
                elif item['type'] == 'move':
                    # Add move segment
                    end_pos = QPointF(item['x'], item['y'])
                    segments.append({
                        'start': current_pos,
                        'end': end_pos,
                        'type': 'move'
                    })
                    current_pos = end_pos

        except Exception as e:
            logger.error(f"Error processing sequence: {e}")

        return segments

    def paintEvent(self, event) -> None:
        """Draw the sequence visualization."""
        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw stage outline
            self._draw_stage(painter)

            # Draw sprayable area
            self._draw_sprayable_area(painter)

            # Draw path segments
            self._draw_path_segments(painter)

        except Exception as e:
            logger.error(f"Error painting visualization: {e}")

    def _draw_stage(self, painter: QPainter) -> None:
        """Draw stage outline."""
        try:
            pen = QPen(QColor(100, 100, 100))
            pen.setWidth(2)
            painter.setPen(pen)

            # Calculate scaled dimensions
            scale = self._calculate_scale()
            width = self._stage['x'] * scale
            height = self._stage['y'] * scale

            # Center in widget
            x = (self.width() - width) / 2
            y = (self.height() - height) / 2

            painter.drawRect(int(x), int(y), int(width), int(height))

        except Exception as e:
            logger.error(f"Error drawing stage: {e}")

    def _draw_sprayable_area(self, painter: QPainter) -> None:
        """Draw sprayable area outline."""
        try:
            pen = QPen(QColor(0, 255, 0))
            pen.setWidth(1)
            pen.setStyle(Qt.PenStyle.DashLine)
            painter.setPen(pen)

            # Calculate scaled dimensions
            scale = self._calculate_scale()
            width = self._substrate['sprayable']['width'] * scale
            height = self._substrate['sprayable']['height'] * scale

            # Center in widget
            x = (self.width() - width) / 2
            y = (self.height() - height) / 2

            painter.drawRect(int(x), int(y), int(width), int(height))

        except Exception as e:
            logger.error(f"Error drawing sprayable area: {e}")

    def _draw_path_segments(self, painter: QPainter) -> None:
        """Draw sequence path segments."""
        try:
            scale = self._calculate_scale()

            for i, segment in enumerate(self._path_segments):
                # Set segment style
                if segment['type'] == 'spray':
                    pen = QPen(QColor(0, 0, 255))
                    pen.setWidth(2)
                    pen.setStyle(Qt.PenStyle.SolidLine)
                else:
                    pen = QPen(QColor(128, 128, 128))
                    pen.setWidth(1)
                    pen.setStyle(Qt.PenStyle.DashLine)

                # Highlight active step
                if i == self._active_step:
                    pen.setColor(QColor(255, 165, 0))  # Orange
                    pen.setWidth(3)

                painter.setPen(pen)

                # Scale and center points
                start = self._transform_point(segment['start'], scale)
                end = self._transform_point(segment['end'], scale)

                painter.drawLine(start, end)

        except Exception as e:
            logger.error(f"Error drawing path segments: {e}")

    def _calculate_scale(self) -> float:
        """Calculate scale factor to fit visualization in widget."""
        try:
            margin = 40  # Pixels of margin

            # Get available space
            available_width = self.width() - (2 * margin)
            available_height = self.height() - (2 * margin)

            # Calculate scale factors
            width_scale = available_width / self._stage['x']
            height_scale = available_height / self._stage['y']

            # Use smaller scale to maintain aspect ratio
            return min(width_scale, height_scale)

        except Exception as e:
            logger.error(f"Error calculating scale: {e}")
            return 1.0

    def _transform_point(self, point: QPointF, scale: float) -> QPointF:
        """Transform a point from stage coordinates to widget coordinates."""
        try:
            # Scale point
            scaled_x = point.x() * scale
            scaled_y = point.y() * scale

            # Center in widget
            centered_x = (self.width() / 2) + scaled_x
            centered_y = (self.height() / 2) + scaled_y

            return QPointF(centered_x, centered_y)

        except Exception as e:
            logger.error(f"Error transforming point: {e}")
            return QPointF(0, 0)

    def _process_pattern(
            self, pattern: Dict[str, Any], start_pos: QPointF) -> List[Dict[str, Any]]:
        """Process pattern data into drawable segments.

        Args:
            pattern: Pattern data dictionary
            start_pos: Starting position for pattern

        Returns:
            List of path segments
        """
        segments = []
        try:
            pattern_type = pattern.get('type')
            params = pattern.get('parameters', {})

            if pattern_type == 'raster':
                # Process raster pattern
                width = params.get('width', 0.0)
                height = params.get('height', 0.0)
                line_spacing = params.get('line_spacing', 1.0)

                current_pos = QPointF(start_pos)

                # Add horizontal lines
                y = 0.0
                while y <= height:
                    # Forward line
                    end_pos = QPointF(
                        current_pos.x() + width, current_pos.y() + y)
                    segments.append({
                        'start': QPointF(current_pos),
                        'end': end_pos,
                        'type': 'spray'
                    })

                    y += line_spacing

                    if y <= height:
                        # Return line
                        start_pos_return = QPointF(end_pos)
                        end_pos_return = QPointF(
                            current_pos.x(), current_pos.y() + y)
                        segments.append({
                            'start': start_pos_return,
                            'end': end_pos_return,
                            'type': 'spray'
                        })

                    y += line_spacing

            elif pattern_type == 'spiral':
                # Process spiral pattern
                # TODO: Implement spiral pattern
                pass  # Remove unused variables

            # Add other pattern types as needed

        except Exception as e:
            logger.error(f"Error processing pattern: {e}")

        return segments

    def update_sequence(self, sequence_data: List[Dict[str, Any]]) -> None:
        """Update the visualization with new sequence data.

        Args:
            sequence_data: List of sequence steps
        """
        try:
            self._path_segments = self._process_sequence(sequence_data)
            self.update()  # Trigger repaint
        except Exception as e:
            logger.error(f"Error updating sequence visualization: {e}")
