"""Main application window."""
from typing import Optional, Dict, Any
import asyncio
from loguru import logger
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, 
    QVBoxLayout, QHBoxLayout, QLabel,
    QFrame, QStatusBar
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QCloseEvent

from micro_cold_spray.core.config.config_manager import ConfigManager
from micro_cold_spray.core.infrastructure.messaging.message_broker import MessageBroker
from micro_cold_spray.core.components.ui.managers.ui_update_manager import UIUpdateManager
from micro_cold_spray.core.components.ui.widgets.status.connection_status import ConnectionStatus
from micro_cold_spray.core.components.ui.tabs.dashboard_tab import DashboardTab
from micro_cold_spray.core.components.ui.widgets.base_widget import BaseWidget
from micro_cold_spray.core.components.ui.tabs.motion_tab import MotionTab
from micro_cold_spray.core.components.ui.tabs.editor_tab import EditorTab
from micro_cold_spray.core.components.ui.tabs.config_tab import ConfigTab
from micro_cold_spray.core.components.ui.tabs.diagnostics_tab import DiagnosticsTab
from micro_cold_spray.core.infrastructure.tags.tag_manager import TagManager

class SystemStateDisplay(BaseWidget):
    """Widget for displaying system state."""
    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="widget_system_state",
            ui_manager=ui_manager,
            update_tags=["system.state"],
            parent=parent
        )
        self.label = QLabel("System: STARTUP")
        self.label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        self.label.setFixedWidth(120)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        if "system.state" in data:
            state = data["system.state"]
            self.label.setText(f"System: {state}")

class SystemMessageDisplay(BaseWidget):
    """Widget for displaying system messages."""
    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="widget_system_message",
            ui_manager=ui_manager,
            update_tags=["system.message"],
            parent=parent
        )
        self.label = QLabel("System starting in disconnected mode")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        if "system.message" in data:
            message = data["system.message"]
            self.label.setText(message)

class SystemErrorDisplay(BaseWidget):
    """Widget for displaying system errors."""
    def __init__(self, ui_manager: UIUpdateManager, parent=None):
        super().__init__(
            widget_id="widget_system_error",
            ui_manager=ui_manager,
            update_tags=["system.error"],
            parent=parent
        )
        self.label = QLabel("No errors")
        self.label.setStyleSheet("color: #27ae60;")
        layout = QHBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        if "system.error" in data:
            error = data["system.error"]
            self.label.setText(error)
            self.label.setStyleSheet("color: #e74c3c;")

class MainWindow(QMainWindow):
    """Main application window."""
    
    def __init__(
        self,
        config_manager: ConfigManager,
        message_broker: MessageBroker,
        ui_manager: UIUpdateManager,
        tag_manager: TagManager
    ) -> None:
        """Initialize main window."""
        super().__init__()
        
        # Track window state
        self.is_closing = False
        
        # Store dependencies
        self._config_manager = config_manager
        self._message_broker = message_broker
        self._ui_manager = ui_manager
        self._tag_manager = tag_manager
        
        # Initialize UI
        self._init_ui()
        
    def _init_ui(self) -> None:
        """Initialize the main window UI."""
        # Set fixed window size
        self.setFixedSize(1200, 900)
        self.setWindowTitle('Micro Cold Spray')
        
        # Create central widget and main layout
        central_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)  # Tight margins
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Create top strip
        top_strip = QFrame()
        top_strip.setFrameShape(QFrame.Shape.StyledPanel)
        top_strip.setFrameShadow(QFrame.Shadow.Raised)
        top_strip.setFixedHeight(40)
        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(5, 2, 5, 2)  # Very tight margins
        top_strip.setLayout(top_layout)
        
        # Left side - System State
        self.system_state = SystemStateDisplay(self._ui_manager)
        top_layout.addWidget(self.system_state)
        
        # Center - Message Area
        message_frame = QFrame()
        message_frame.setFrameShape(QFrame.Shape.StyledPanel)
        message_frame.setFrameShadow(QFrame.Shadow.Sunken)
        message_layout = QVBoxLayout()
        message_layout.setContentsMargins(5, 2, 5, 2)  # Reduced margins
        message_layout.setSpacing(0)  # Remove spacing

        # Style the message display with both vertical and horizontal alignment
        self.current_message = SystemMessageDisplay(self._ui_manager)
        self.current_message.setStyleSheet("""
            QLabel {
                padding: 0;
                margin: 0;
                min-height: 20px;
                qproperty-alignment: AlignCenter;  /* Center both horizontally and vertically */
            }
        """)
        message_layout.addWidget(self.current_message, alignment=Qt.AlignmentFlag.AlignCenter)  # Center in layout
        message_frame.setLayout(message_layout)
        top_layout.addWidget(message_frame, stretch=1)
        
        # Add minimal spacing before connection status
        top_layout.addSpacing(5)
        
        # Right side - Connection Status and User
        self.connection_status = ConnectionStatus(self._ui_manager)
        self.connection_status.setFixedWidth(300)
        top_layout.addWidget(self.connection_status)
        
        # Add top strip to main layout
        main_layout.addWidget(top_strip)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Create and add tabs
        self.dashboard_tab = DashboardTab(self._ui_manager)
        self.motion_tab = MotionTab(self._ui_manager)
        self.editor_tab = EditorTab(self._ui_manager)
        self.config_tab = ConfigTab(self._ui_manager)
        self.diagnostics_tab = DiagnosticsTab(self._ui_manager)
        
        self.tab_widget.addTab(self.dashboard_tab, "Dashboard")
        self.tab_widget.addTab(self.motion_tab, "Motion")
        self.tab_widget.addTab(self.editor_tab, "Editor")
        self.tab_widget.addTab(self.diagnostics_tab, "Diagnostics")
        self.tab_widget.addTab(self.config_tab, "Config")
        
        main_layout.addWidget(self.tab_widget)
        
        # Create status bar for errors
        self.status_bar = QStatusBar()
        self.status_bar.setMinimumHeight(30)
        self.status_bar.setStyleSheet("""
            QStatusBar {
                border-top: 1px solid #cccccc;
                background-color: #f5f5f5;
                padding: 4px 8px;
                font-size: 12px;
                min-height: 40px;
                margin: 0;
            }
            QStatusBar::item {
                border: none;
                padding: 0;
            }
            QLabel {
                padding: 4px 0;
                margin: 0;
            }
        """)
        
        # Add permanent widget for error display
        self.error_label = SystemErrorDisplay(self._ui_manager)
        self.status_bar.addPermanentWidget(self.error_label, 1)
        
        self.setStatusBar(self.status_bar)

    async def _cleanup(self) -> None:
        """Clean up all widgets and resources."""
        try:
            # Clean up tabs first
            if hasattr(self, 'dashboard_tab') and self.dashboard_tab is not None:
                try:
                    await self.dashboard_tab.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up dashboard tab: {e}")
                
            if hasattr(self, 'motion_tab') and self.motion_tab is not None:
                try:
                    await self.motion_tab.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up motion tab: {e}")
                
            if hasattr(self, 'editor_tab') and self.editor_tab is not None:
                try:
                    await self.editor_tab.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up editor tab: {e}")
                
            if hasattr(self, 'diagnostics_tab') and self.diagnostics_tab is not None:
                try:
                    await self.diagnostics_tab.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up diagnostics tab: {e}")
                
            if hasattr(self, 'config_tab') and self.config_tab is not None:
                try:
                    await self.config_tab.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up config tab: {e}")
            
            # Clean up main window widgets
            if hasattr(self, 'system_state') and self.system_state is not None:
                try:
                    await self.system_state.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up system state: {e}")
                
            if hasattr(self, 'current_message') and self.current_message is not None:
                try:
                    await self.current_message.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up current message: {e}")
                
            if hasattr(self, 'error_label') and self.error_label is not None:
                try:
                    await self.error_label.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up error label: {e}")
            
            if self._ui_manager is not None:
                try:
                    await self._ui_manager.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up UI manager: {e}")
            
            self.is_closing = True
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    def closeEvent(self, event: QCloseEvent) -> None:
        """Handle window close event."""
        self.is_closing = True
        event.accept()