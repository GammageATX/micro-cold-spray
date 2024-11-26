"""Process validation display widget."""
from typing import Dict, Any, Optional
import logging
from datetime import datetime
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTreeWidget, QTreeWidgetItem
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

from ..base_widget import BaseWidget
from ...managers.ui_update_manager import UIUpdateManager

logger = logging.getLogger(__name__)

class ValidationPanel(BaseWidget):
    """Displays process validation status."""
    
    # Status colors
    STATUS_COLORS = {
        'valid': '#4CAF50',    # Green
        'invalid': '#F44336',  # Red
        'warning': '#FF9800',  # Orange
        'checking': '#2196F3'  # Blue
    }
    
    # Validation groups
    VALIDATION_GROUPS = {
        'chamber': {
            'name': 'Chamber Status',
            'checks': [
                'chamber_pressure_stable',
                'vacuum_ready',
                'gate_valve_position'
            ]
        },
        'gas': {
            'name': 'Gas System',
            'checks': [
                'main_flow_stable',
                'feeder_flow_stable',
                'nozzle_pressure_stable'
            ]
        },
        'motion': {
            'name': 'Motion System',
            'checks': [
                'position_valid',
                'motion_enabled',
                'in_limits'
            ]
        },
        'process': {
            'name': 'Process Status',
            'checks': [
                'process_ready',
                'powder_feed_ready',
                'spray_conditions_met'
            ]
        }
    }

    def __init__(
        self,
        ui_manager: UIUpdateManager,
        parent=None
    ):
        super().__init__(
            widget_id="widget_diagnostics_validation",
            ui_manager=ui_manager,
            update_tags=[
                "validation/*",
                "process/status_update"
            ],
            parent=parent
        )
        
        # Track validation states
        self._validation_states: Dict[str, bool] = {}
        self._group_items: Dict[str, QTreeWidgetItem] = {}
        
        self._init_ui()
        logger.info("Validation panel initialized")

    async def handle_ui_update(self, data: Dict[str, Any]) -> None:
        """Handle UI updates."""
        try:
            if "validation" in data:
                validation = data["validation"]
                for check, status in validation.items():
                    # Determine group from check name
                    group = next(
                        (g for g, info in self.VALIDATION_GROUPS.items() 
                         if check in info['checks']),
                        None
                    )
                    
                    if group:
                        self._update_check_status(group, check, status)
                        
            elif "process/status_update" in data:
                if "validation" in data:
                    validation = data["validation"]
                    for check, status in validation.items():
                        # Determine group from check name
                        group = next(
                            (g for g, info in self.VALIDATION_GROUPS.items() 
                             if check in info['checks']),
                            None
                        )
                        
                        if group:
                            self._update_check_status(group, check, status)
                            
        except Exception as e:
            logger.error(f"Error handling UI update: {e}")

    def _init_ui(self) -> None:
        """Setup validation panel UI."""
        layout = QVBoxLayout()
        
        # Create validation tree
        self.validation_tree = QTreeWidget()
        self.validation_tree.setHeaderLabels(["Check", "Status", "Last Update"])
        self.validation_tree.setColumnWidth(0, 200)  # Name column
        self.validation_tree.setColumnWidth(1, 100)  # Status column
        
        # Create group items
        for group_id, group_info in self.VALIDATION_GROUPS.items():
            group_item = QTreeWidgetItem([group_info['name']])
            self.validation_tree.addTopLevelItem(group_item)
            self._group_items[group_id] = group_item
            
            # Add check items
            for check in group_info['checks']:
                check_item = QTreeWidgetItem([
                    check.replace('_', ' ').title(),
                    'Checking...',
                    'Never'
                ])
                group_item.addChild(check_item)
                
        layout.addWidget(self.validation_tree)
        
        # Overall status
        status_layout = QHBoxLayout()
        self.status_label = QLabel("Overall Status:")
        self.status_value = QLabel("Checking...")
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.status_value)
        layout.addLayout(status_layout)
        
        self.setLayout(layout)

    def _update_check_status(
        self,
        group: str,
        check: str,
        status: bool,
        message: Optional[str] = None
    ) -> None:
        """Update check status in tree."""
        try:
            # Find group item
            group_item = self._group_items.get(group)
            if not group_item:
                return
                
            # Find check item
            for i in range(group_item.childCount()):
                check_item = group_item.child(i)
                if check_item.text(0).lower().replace(' ', '_') == check:
                    # Update status
                    status_text = "Valid" if status else "Invalid"
                    if message:
                        status_text += f" ({message})"
                        
                    check_item.setText(1, status_text)
                    check_item.setText(2, datetime.now().strftime("%H:%M:%S"))
                    
                    # Set color
                    color = self.STATUS_COLORS['valid' if status else 'invalid']
                    check_item.setForeground(1, QColor(color))
                    break
                    
            # Update group status
            self._update_group_status(group)
            
        except Exception as e:
            logger.error(f"Error updating check status: {e}")

    def _update_group_status(self, group: str) -> None:
        """Update group status based on checks."""
        try:
            group_item = self._group_items.get(group)
            if not group_item:
                return
                
            # Check all children
            valid_count = 0
            total_count = group_item.childCount()
            
            for i in range(total_count):
                check_item = group_item.child(i)
                if check_item.text(1).startswith("Valid"):
                    valid_count += 1
                    
            # Update group status
            if valid_count == total_count:
                status = "All Valid"
                color = self.STATUS_COLORS['valid']
            elif valid_count == 0:
                status = "All Invalid"
                color = self.STATUS_COLORS['invalid']
            else:
                status = f"{valid_count}/{total_count} Valid"
                color = self.STATUS_COLORS['warning']
                
            group_item.setText(1, status)
            group_item.setForeground(1, QColor(color))
            
            # Update overall status
            self._update_overall_status()
            
        except Exception as e:
            logger.error(f"Error updating group status: {e}")

    def _update_overall_status(self) -> None:
        """Update overall validation status."""
        try:
            valid_groups = 0
            total_groups = len(self._group_items)
            
            for group_item in self._group_items.values():
                if group_item.text(1).startswith("All Valid"):
                    valid_groups += 1
                    
            if valid_groups == total_groups:
                status = "All Systems Valid"
                color = self.STATUS_COLORS['valid']
            elif valid_groups == 0:
                status = "Systems Invalid"
                color = self.STATUS_COLORS['invalid']
            else:
                status = f"{valid_groups}/{total_groups} Systems Valid"
                color = self.STATUS_COLORS['warning']
                
            self.status_value.setText(status)
            self.status_value.setStyleSheet(f"color: {color}")
            
        except Exception as e:
            logger.error(f"Error updating overall status: {e}")