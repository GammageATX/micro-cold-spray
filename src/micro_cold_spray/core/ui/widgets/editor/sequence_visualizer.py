"""Visualizes the spray sequence path on a 2D representation of the stage."""
import logging
from typing import Any, Dict, List, Optional
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget
from ....infrastructure.messaging.message_broker import MessageBroker
import asyncio
import math
from datetime import datetime

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
            update_tags=["error"],
            parent=parent
        )

        self._message_broker = message_broker
        self._pending_requests = {}  # Track pending requests by ID

        # Initialize with default values
        self._stage = {'x': 200.0, 'y': 200.0}  # Default stage size
        self._substrate = {
            'sprayable': {'width': 141.0, 'height': 141.0}
        }  # Default substrate size

        # Store sequence path data
        self._path_segments: List[Dict[str, Any]] = []  # List of {start, end, type} dicts
        self._active_step: Optional[int] = None

        # Set white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(palette)

        self.setMinimumSize(400, 400)

        # Subscribe to response topics
        asyncio.create_task(self._subscribe_to_topics())
        logger.info("Sequence visualizer initialized")

    async def _subscribe_to_topics(self) -> None:
        """Subscribe to required message topics."""
        try:
            await self._message_broker.subscribe("motion/response", self._handle_motion_response)
            await self._message_broker.subscribe("motion/state", self._handle_motion_state)
            await self._message_broker.subscribe("sequence/response", self._handle_sequence_response)
            await self._message_broker.subscribe("sequence/state", self._handle_sequence_state)

            # Request initial dimensions
            await self._request_dimensions()

        except Exception as e:
            logger.error(f"Error subscribing to topics: {e}")

    async def _handle_motion_response(self, data: Dict[str, Any]) -> None:
        """Handle motion response messages."""
        try:
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            expected_type, _ = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Motion operation failed: {data.get('error')}")
                return

            if expected_type == "dimensions":
                if "stage" in data:
                    self._stage = data["stage"]
                if "substrate" in data:
                    self._substrate = data["substrate"]
                self.update()  # Trigger repaint

        except Exception as e:
            logger.error(f"Error handling motion response: {e}")

    async def _handle_sequence_response(self, data: Dict[str, Any]) -> None:
        """Handle sequence response messages."""
        try:
            request_id = data.get("request_id")
            if not request_id or request_id not in self._pending_requests:
                return

            expected_type, _ = self._pending_requests.pop(request_id)
            if data.get("request_type") != expected_type:
                logger.warning(f"Mismatched request type for {request_id}")
                return

            if not data.get("success"):
                logger.error(f"Sequence operation failed: {data.get('error')}")
                return

            if expected_type == "path":
                path_data = data.get("data", {})
                if path_data:
                    self._path_segments = self._process_sequence(path_data)
                    self.update()  # Trigger repaint

        except Exception as e:
            logger.error(f"Error handling sequence response: {e}")

    async def _request_dimensions(self) -> None:
        """Request stage and substrate dimensions."""
        try:
            request_id = f"dimensions_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "motion/request",
                {
                    "request_id": request_id,
                    "request_type": "dimensions"
                }
            )
            self._pending_requests[request_id] = ("dimensions", None)
            logger.debug(f"Requested motion dimensions: {request_id}")

        except Exception as e:
            logger.error(f"Error requesting dimensions: {e}")

    async def update_sequence(self, sequence_data: List[Dict[str, Any]]) -> None:
        """Update the visualization with new sequence data."""
        try:
            request_id = f"path_{datetime.now().timestamp()}"
            await self._message_broker.publish(
                "sequence/request",
                {
                    "request_id": request_id,
                    "request_type": "path",
                    "sequence": sequence_data
                }
            )
            self._pending_requests[request_id] = ("path", None)
            logger.debug(f"Requested sequence path: {request_id}")

        except Exception as e:
            logger.error(f"Error updating sequence visualization: {e}")

    def _process_sequence(self, sequence_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process sequence data into drawable path segments."""
        segments = []
        current_pos = QPointF(0, 0)  # Start at origin

        try:
            for item in sequence_data:
                if item['type'] == 'pattern':
                    # Process pattern path points
                    pattern_segments = self._process_pattern(item['pattern'], current_pos)
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
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            ))

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
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            ))

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
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            ))

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
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            ))

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
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            ))

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
        """Process pattern data into drawable segments."""
        segments = []
        try:
            pattern_type = pattern.get('type')
            params = pattern.get('params', {})  # Changed from parameters to params to match file format

            if pattern_type == 'serpentine':
                # Process serpentine pattern
                length = params.get('length', 0.0)
                width = params.get('width', 0.0)  # Added width parameter
                spacing = params.get('spacing', 1.0)
                direction = params.get('direction', 'posY')  # Added direction parameter

                current_pos = QPointF(start_pos)
                
                # Determine direction multiplier
                y_multiplier = -1 if direction == 'negY' else 1

                # Add horizontal lines
                y = 0.0
                while y <= width:
                    # Forward line
                    end_pos = QPointF(current_pos.x() + length, current_pos.y() + (y * y_multiplier))
                    segments.append({
                        'start': QPointF(current_pos.x(), current_pos.y() + (y * y_multiplier)),
                        'end': end_pos,
                        'type': 'spray'
                    })

                    y += spacing

                    if y <= width:
                        # Return line
                        start_pos_return = QPointF(end_pos)
                        end_pos_return = QPointF(
                            current_pos.x(), current_pos.y() + ((y) * y_multiplier))
                        segments.append({
                            'start': start_pos_return,
                            'end': end_pos_return,
                            'type': 'spray'
                        })

                    y += spacing

            elif pattern_type == 'spiral':
                # Process spiral pattern
                # Get spiral parameters
                diameter = params.get('diameter', 0.0)
                pitch = params.get('pitch', 1.0)
                
                # Calculate number of revolutions based on diameter and pitch
                revolutions = diameter / (2 * pitch)
                
                # Initialize first point at center
                current_point = QPointF(current_pos.x(), current_pos.y())
                
                # Generate points along spiral
                theta = 0.0
                step = 0.1  # Adjust step size for smoothness
                
                while theta <= revolutions * 2 * math.pi:
                    # Calculate current radius
                    r = (theta / (2 * math.pi)) * pitch
                    
                    # Calculate next point coordinates
                    next_x = current_pos.x() + r * math.cos(theta)
                    next_y = current_pos.y() + r * math.sin(theta)
                    next_point = QPointF(next_x, next_y)
                    
                    # Create segment (except for first point)
                    if theta > 0:
                        segments.append({
                            'start': current_point,
                            'end': next_point,
                            'type': 'spray'
                        })
                    
                    # Update current point for next segment
                    current_point = next_point
                    theta += step

            # Add other pattern types as needed

        except Exception as e:
            logger.error(f"Error processing pattern: {e}")
            logger.exception("Pattern processing error details:")

        return segments

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during sequence visualizer cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "sequence_visualizer",
                    "message": str(e),
                    "level": "error"
                }
            )

    async def _handle_motion_state(self, data: Dict[str, Any]) -> None:
        """Handle motion state messages."""
        try:
            state = data.get("state")
            if state == "dimensions_changed":
                # Request updated dimensions
                request_id = f"dimensions_{datetime.now().timestamp()}"
                await self._message_broker.publish(
                    "motion/request",
                    {
                        "request_id": request_id,
                        "request_type": "dimensions"
                    }
                )
                self._pending_requests[request_id] = ("dimensions", None)
                logger.debug(f"Requested updated dimensions: {request_id}")

        except Exception as e:
            logger.error(f"Error handling motion state: {e}")

    async def _handle_sequence_state(self, data: Dict[str, Any]) -> None:
        """Handle sequence state messages."""
        try:
            state = data.get("state")
            if state == "active_step":
                self._active_step = data.get("step")
                self.update()  # Trigger repaint
            elif state == "stopped":
                self._active_step = None
                self.update()  # Trigger repaint

        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")
