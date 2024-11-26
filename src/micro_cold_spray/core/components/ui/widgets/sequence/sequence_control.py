"""Sequence control widget for loading and controlling sequences."""
from typing import Dict, Any, Optional, Protocol, runtime_checkable
import logging
from pathlib import Path
import yaml
import time
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QLabel, 
    QFrame, QPushButton, QComboBox, QProgressBar
)
from PySide6.QtCore import Qt
import asyncio
from functools import partial

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager
from .....infrastructure.messaging.message_broker import MessageBroker

logger = logging.getLogger(__name__)

@runtime_checkable
class MainWindowProtocol(Protocol):
    """Protocol for main window interface."""
    @property
    def connection_status(self) -> Any:
        """Get connection status widget."""
        ...

class CustomProgressBar(QProgressBar):
    """Custom progress bar with centered text regardless of value."""
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTextVisible(True)
        self.setStyleSheet("""
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                background-color: #2c3e50;
                color: white;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #27ae60;
            }
        """)

class SequenceControl(BaseWidget):
    """Widget for sequence loading and control."""
    
    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="control_dashboard_sequence",
            ui_manager=ui_manager,
            update_tags=[
                "sequence.state",
                "sequence.progress",
                "sequence.error",
                "system.state",
                "system.connection",
                "system.message"
            ],
            parent=parent
        )
        
        self._sequences = {}
        self._system_state = "STARTUP"
        self._connection_state = {"connected": False}
        
        self._init_ui()
        self._load_sequence_library()
        logger.info("Sequence control initialized")

    def _init_ui(self) -> None:
        """Initialize the sequence control UI."""
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Create frame
        frame = QFrame()
        frame.setFrameShape(QFrame.Shape.StyledPanel)
        frame.setFrameShadow(QFrame.Shadow.Raised)
        frame_layout = QVBoxLayout()
        
        # Add title
        title = QLabel("Sequence Control")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        frame_layout.addWidget(title)
        
        # Sequence Selection
        select_layout = QHBoxLayout()
        select_label = QLabel("Sequence:")
        self.sequence_combo = QComboBox()
        self.sequence_combo.setMinimumWidth(200)
        self.sequence_combo.addItem("")  # Blank default option
        self.load_button = QPushButton("Load")
        select_layout.addWidget(select_label)
        select_layout.addWidget(self.sequence_combo)
        select_layout.addWidget(self.load_button)
        frame_layout.addLayout(select_layout)
        
        # Status Display
        self.status_label = QLabel("Status: No Sequence Selected")
        self.status_label.setStyleSheet("color: gray; margin-top: 5px;")
        frame_layout.addWidget(self.status_label)
        
        # Progress Bar
        self.progress_bar = CustomProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setMinimumHeight(25)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Ready")
        frame_layout.addWidget(self.progress_bar)
        
        # Control Buttons
        button_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start Sequence")
        self.cancel_button = QPushButton("Cancel")
        
        # Initially disable control buttons
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        
        # Add buttons to layout
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.cancel_button)
        
        frame_layout.addLayout(button_layout)
        
        # Set frame layout
        frame.setLayout(frame_layout)
        layout.addWidget(frame)
        
        # Add stretch to keep widget compact
        layout.addStretch()
        
        self.setLayout(layout)
        
        # Connect signals with async handlers
        self.load_button.clicked.connect(
            lambda: asyncio.create_task(self._on_load_clicked())
        )
        self.start_button.clicked.connect(
            lambda: asyncio.create_task(self._on_start_clicked())
        )
        self.cancel_button.clicked.connect(
            lambda: asyncio.create_task(self._on_cancel_clicked())
        )
        self.sequence_combo.currentTextChanged.connect(self._on_sequence_selected)

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle updates from UIUpdateManager."""
        try:
            if "system.state" in data:
                old_state = self._system_state
                self._system_state = data["system.state"]
                logger.debug(f"System state changed: {old_state} -> {self._system_state}")
                await self._update_button_states()
                
            elif "system.connection" in data:
                old_connected = self._connection_state.get("connected", False)
                self._connection_state = data["system.connection"]
                logger.debug(f"Connection state changed: {old_connected} -> {self._connection_state.get('connected')}")
                await self._update_button_states()
                
            elif "sequence.state" in data:
                sequence_state = data["sequence.state"]
                self._handle_sequence_state(sequence_state)
                logger.debug(f"Sequence state update: {sequence_state}")
                
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")
            await self.send_update("system.error", f"Sequence control error: {str(e)}")

    async def _update_button_states(self):
        """Update button states based on system state."""
        try:
            sequence_loaded = self.sequence_combo.currentText() != ""
            connected = self._connection_state.get("connected", False)
            system_ready = self._system_state in ["READY", "IDLE"]
            
            # Always allow loading sequences
            self.load_button.setEnabled(True)
            
            # Start button requires sequence loaded AND either:
            # - System connected and ready, OR
            # - System in disconnected simulation mode
            can_start = sequence_loaded and (
                (connected and system_ready) or 
                (not connected and self._system_state in ["STARTUP", "READY", "IDLE"])
            )
            
            self.start_button.setEnabled(can_start)
            
            # Cancel only enabled when sequence is running
            self.cancel_button.setEnabled(self._system_state == "RUNNING")
            
            # Update status display
            if not sequence_loaded:
                await self.send_update("system.message", "No sequence loaded")
            elif not can_start:
                if not connected:
                    await self.send_update("system.message", "System disconnected")
                elif not system_ready:
                    await self.send_update("system.message", f"System in {self._system_state} state")
            else:
                self.status_label.setText("Status: Ready to start")
                
            logger.debug(f"Button states updated - Start: {can_start}, Cancel: {self._system_state == 'RUNNING'}")
            
        except Exception as e:
            logger.error(f"Error updating button states: {e}")
            await self.send_update("system.error", f"Error updating controls: {str(e)}")
    
    def _load_sequence_library(self):
        """Load available sequences from the library directory."""
        try:
            library_path = Path("data/sequences/library")
            if not library_path.exists():
                logger.warning(f"Sequence library path not found: {library_path}")
                return
                
            # Load all yaml files from the library
            for sequence_file in library_path.glob("*.yaml"):
                try:
                    with open(sequence_file, 'r') as f:
                        sequence_data = yaml.safe_load(f)
                        
                    # Extract sequence name from metadata
                    if sequence_data and 'sequence' in sequence_data:
                        metadata = sequence_data['sequence'].get('metadata', {})
                        name = metadata.get('name')
                        if name:
                            self._sequences[name] = sequence_data
                            self.sequence_combo.addItem(name)
                            
                except Exception as e:
                    logger.error(f"Error loading sequence file {sequence_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Error loading sequence library: {str(e)}")
            
    def _on_sequence_selected(self, sequence_name: str):
        """Handle sequence selection change."""
        if not sequence_name:  # Blank selection
            self.load_button.setEnabled(False)
            self.start_button.setEnabled(False)
            self.status_label.setText("Status: No Sequence Selected")
            self.status_label.setStyleSheet("color: gray;")  # Reset color
        else:
            self.load_button.setEnabled(True)
            self.status_label.setStyleSheet("")  # Reset to default color
            
    def _handle_sequence_state(self, state: str) -> None:
        """Handle sequence state changes."""
        try:
            if state == "RUNNING":
                self.cancel_button.setEnabled(True)
                self.start_button.setEnabled(False)
                self.status_label.setText("Status: Running sequence")
                self.status_label.setStyleSheet("color: blue;")
            elif state == "COMPLETED":
                self.cancel_button.setEnabled(False)
                self.start_button.setEnabled(True)
                self.status_label.setText("Status: Sequence completed")
                self.status_label.setStyleSheet("color: green;")
            elif state == "ERROR":
                self.cancel_button.setEnabled(False)
                self.start_button.setEnabled(True)
                self.status_label.setText("Status: Sequence error")
                self.status_label.setStyleSheet("color: red;")
            elif state == "CANCELLED":
                self.cancel_button.setEnabled(False)
                self.start_button.setEnabled(True)
                self.status_label.setText("Status: Sequence cancelled")
                self.status_label.setStyleSheet("")
                
        except Exception as e:
            logger.error(f"Error handling sequence state: {e}")
            # Don't re-raise since this is an internal state change

    async def _on_load_clicked(self) -> None:
        """Handle load button click."""
        try:
            selected = self.sequence_combo.currentText()
            if not selected:
                self.start_button.setEnabled(False)
                self.cancel_button.setEnabled(False)
                self.update_progress(0)
                self.status_label.setText("Status: No Sequence Selected")
                self.status_label.setStyleSheet("color: gray;")
                return
                
            if selected in self._sequences:
                sequence_data = self._sequences[selected]
                self.start_button.setEnabled(True)
                self.cancel_button.setEnabled(False)
                self.status_label.setText(f"Loaded: {selected}")
                self.status_label.setStyleSheet("")
                self.progress_bar.setValue(0)
                self.progress_bar.setFormat("Ready")
                
                # Get user from parent window's connection status
                parent_window = self.window()
                user = "Default User"
                
                if isinstance(parent_window, MainWindowProtocol):
                    user = parent_window.connection_status.user_combo.currentText()
                else:
                    logger.warning("Could not find main window, using default user")
                
                # Create sequence loaded data
                sequence_loaded_data = {
                    "name": selected,
                    "user": user,
                    "metadata": sequence_data.get("sequence", {}).get("metadata", {}),
                    "timestamp": time.time()
                }
                
                # Add debug logging
                logger.debug(f"Sending sequence.loaded update: {sequence_loaded_data}")
                
                # Send only through UIUpdateManager
                await self.send_update(
                    "sequence.loaded",
                    sequence_loaded_data
                )
                
        except Exception as e:
            logger.error(f"Error loading sequence: {e}")
            await self.send_update("system.error", f"Error loading sequence: {str(e)}")

    async def _on_start_clicked(self) -> None:
        """Handle start button click."""
        try:
            # Check system state and connection
            if not self._connection_state.get("connected", False):
                self.status_label.setText("Cannot start: System disconnected")
                self.status_label.setStyleSheet("color: red;")
                # Send warning to system
                await self.send_update(
                    "system.message",
                    "Cannot start sequence in disconnected state"
                )
                return
            
            if self._system_state not in ["READY", "IDLE"]:
                self.status_label.setText(f"Cannot start: System {self._system_state}")
                self.status_label.setStyleSheet("color: red;")
                return
            
            # If all checks pass, send the start command
            await self.send_update(
                "sequence.command",
                {
                    "command": "start",
                    "sequence": self.sequence_combo.currentText(),
                    "timestamp": time.time()
                }
            )
            
            # Update UI
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat("Starting...")
            self.status_label.setText("Status: Starting sequence...")
            self.status_label.setStyleSheet("color: blue;")
            
        except Exception as e:
            logger.error(f"Error starting sequence: {e}")
            await self.send_update(
                "system.error",
                f"Error starting sequence: {str(e)}"
            )

    async def _on_cancel_clicked(self) -> None:
        """Handle cancel button click."""
        try:
            await self.send_update(
                "sequence.command",
                {
                    "command": "cancel",
                    "timestamp": time.time()
                }
            )
        except Exception as e:
            logger.error(f"Error cancelling sequence: {e}")
            await self.send_update(
                "system.error",
                f"Error cancelling sequence: {str(e)}"
            )

    def update_progress(self, progress: float, step_name: Optional[str] = None) -> None:
        """Update the sequence progress display."""
        self.progress_bar.setValue(int(progress))
        if step_name:
            self.progress_bar.setFormat(f"{progress:.1f}% - {step_name}")
        else:
            self.progress_bar.setFormat(f"{progress:.1f}%")