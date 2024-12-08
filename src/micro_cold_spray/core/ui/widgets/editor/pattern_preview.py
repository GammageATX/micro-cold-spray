"""Widget for displaying pattern previews."""
import logging
from typing import Any, Dict, Optional
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor
from ...managers.ui_update_manager import UIUpdateManager
from ..base_widget import BaseWidget
from ....infrastructure.messaging.message_broker import MessageBroker
import asyncio
import math

logger = logging.getLogger(__name__)


class PatternPreviewWidget(BaseWidget):
    """Widget for displaying pattern previews."""

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        message_broker: MessageBroker,
        parent=None
    ):
        super().__init__(
            widget_id="widget_editor_pattern_preview",
            ui_manager=ui_manager,
            update_tags=[
                "pattern/current",
                "pattern/preview",
                "system/connection",
                "system/error"
            ],
            parent=parent
        )

        self._message_broker = message_broker
        self._pattern: Optional[Dict[str, Any]] = None
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0

        # Set white background
        self.setAutoFillBackground(True)
        palette = self.palette()
        palette.setColor(self.backgroundRole(), Qt.GlobalColor.white)
        self.setPalette(palette)

        self.setMinimumSize(300, 300)
        logger.info("Pattern preview initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "pattern/current" in data:
                pattern_data = data["pattern/current"]
                if isinstance(pattern_data, dict):
                    self._pattern = pattern_data
                    self.update()

            elif "pattern/preview" in data:
                preview_data = data["pattern/preview"]
                if isinstance(preview_data, dict):
                    self._pattern = preview_data
                    self.update()

            elif "system/connection" in data:
                connected = data.get("connected", False)
                if not connected:
                    self._pattern = None
                    self.update()

        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            )

    def paintEvent(self, event) -> None:
        """Draw pattern preview."""
        try:
            if not self._pattern:
                return

            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            # Draw pattern based on type
            pattern_type = self._pattern.get("type", "")
            if pattern_type == "serpentine":
                self._draw_serpentine(painter)
            elif pattern_type == "spiral":
                self._draw_spiral(painter)
            elif pattern_type == "linear":
                self._draw_linear(painter)

        except Exception as e:
            logger.error(f"Error drawing pattern preview: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _draw_serpentine(self, painter: QPainter) -> None:
        """Draw serpentine pattern."""
        try:
            params = self._pattern.get("parameters", {})
            length = float(params.get("length", 50.0))
            width = float(params.get("width", 30.0))
            spacing = float(params.get("spacing", 2.0))
            direction = params.get("direction", "posX")

            # Calculate scale to fit
            scale_x = (self.width() - 40) / length
            scale_y = (self.height() - 40) / width
            self._scale = min(scale_x, scale_y)

            # Center pattern
            self._offset_x = (self.width() - (length * self._scale)) / 2
            self._offset_y = (self.height() - (width * self._scale)) / 2

            # Draw serpentine lines
            pen = QPen(QColor(0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)

            # Adjust start position based on direction
            start_x = length if direction in ["negX", "negY"] else 0
            start_y = width if direction in ["negY", "posY"] else 0

            y = start_y
            while 0 <= y <= width:
                start = self._transform_point(start_x, y)
                end = self._transform_point(length - start_x, y)
                painter.drawLine(start, end)
                y += spacing if direction in ["posX", "posY"] else -spacing

                if 0 <= y <= width:
                    start = self._transform_point(length - start_x, y)
                    end = self._transform_point(start_x, y)
                    painter.drawLine(start, end)
                    y += spacing if direction in ["posX", "posY"] else -spacing

        except Exception as e:
            logger.error(f"Error drawing serpentine pattern: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _draw_spiral(self, painter: QPainter) -> None:
        """Draw spiral pattern."""
        try:
            params = self._pattern.get("parameters", {})
            diameter = float(params.get("diameter", 40.0))
            pitch = float(params.get("pitch", 2.0))
            direction = params.get("direction", "CW")

            # Calculate scale to fit
            scale = (min(self.width(), self.height()) - 40) / diameter
            self._scale = scale

            # Center pattern
            self._offset_x = (self.width() - (diameter * self._scale)) / 2
            self._offset_y = (self.height() - (diameter * self._scale)) / 2

            # Draw spiral
            pen = QPen(QColor(0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)

            # Calculate spiral points
            points = []
            radius = diameter / 2
            revolutions = radius / pitch
            angle_step = math.pi / 180  # 1 degree steps
            
            # Adjust direction
            angle_multiplier = 1 if direction == "CW" else -1
            
            for i in range(int(360 * revolutions)):
                angle = i * angle_step * angle_multiplier
                r = (i * pitch) / (2 * math.pi)
                if r > radius:
                    break
                x = r * math.cos(angle)
                y = r * math.sin(angle)
                points.append(self._transform_point(x, y))

            # Draw spiral segments
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i + 1])

        except Exception as e:
            logger.error(f"Error drawing spiral pattern: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _draw_linear(self, painter: QPainter) -> None:
        """Draw linear pattern."""
        try:
            params = self._pattern.get("parameters", {})
            length = float(params.get("length", 2.0))
            direction = params.get("direction", "posX")

            # Calculate scale to fit
            scale = (min(self.width(), self.height()) - 40) / length
            self._scale = scale

            # Center pattern
            self._offset_x = (self.width() - (length * self._scale)) / 2
            self._offset_y = self.height() / 2

            # Draw line
            pen = QPen(QColor(0, 0, 255))
            pen.setWidth(2)
            painter.setPen(pen)

            if direction in ["posX", "negX"]:
                start = self._transform_point(0, 0)
                end = self._transform_point(length if direction == "posX" else -length, 0)
            else:  # posY or negY
                start = self._transform_point(0, 0)
                end = self._transform_point(0, length if direction == "posY" else -length)

            painter.drawLine(start, end)

        except Exception as e:
            logger.error(f"Error drawing linear pattern: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            ))

    def _transform_point(self, x: float, y: float) -> QPointF:
        """Transform pattern coordinates to widget coordinates."""
        try:
            widget_x = self._offset_x + (x * self._scale)
            widget_y = self._offset_y + (y * self._scale)
            return QPointF(widget_x, widget_y)
        except Exception as e:
            logger.error(f"Error transforming point: {e}")
            asyncio.create_task(self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            ))
            return QPointF(0, 0)

    async def cleanup(self) -> None:
        """Clean up resources."""
        try:
            await super().cleanup()
        except Exception as e:
            logger.error(f"Error during pattern preview cleanup: {e}")
            await self._ui_manager.send_update(
                "system/error",
                {
                    "source": "pattern_preview",
                    "message": str(e),
                    "level": "error"
                }
            )
