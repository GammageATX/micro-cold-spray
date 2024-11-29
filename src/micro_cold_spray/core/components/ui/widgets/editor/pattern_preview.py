from typing import Dict, Any
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt
from PySide6.QtGui import QPainter, QPen

class PatternPreviewWidget(QWidget):
    """Widget for displaying pattern previews."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern = None
        self._scale = 1.0
        self._offset_x = 0
        self._offset_y = 0

    def set_pattern(self, pattern: Dict[str, Any]) -> None:
        """Set pattern to preview."""
        self._pattern = pattern
        self.update()  # Trigger repaint

    def paintEvent(self, event) -> None:
        """Draw pattern preview."""
        if not self._pattern:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw pattern based on type
        pattern_type = self._pattern["pattern"]["type"]
        if pattern_type == "serpentine":
            self._draw_serpentine(painter)
        elif pattern_type == "spiral":
            self._draw_spiral(painter)
        elif pattern_type == "linear":
            self._draw_linear(painter) 