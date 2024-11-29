from typing import Dict, Any, Optional
from loguru import logger
import asyncio
from pathlib import Path
import json
from datetime import datetime
import shutil
import csv
import yaml

from ....infrastructure.messaging.message_broker import MessageBroker
from ....infrastructure.config.config_manager import ConfigManager
from ....exceptions import OperationError

class DataManager:
    """Manages process data collection and storage."""
    
    def __init__(self, message_broker: MessageBroker, config_manager: ConfigManager):
        """Initialize with required dependencies."""
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._process_data: Dict[str, Dict[str, Any]] = {}
        self._data_path = Path("data/process")
        self._current_user: Optional[str] = None
        self._cancelled = False
        self._is_initialized = False
        self._spray_active = False
        self._current_spray = None
        
        logger.info("Data manager initialized")

    async def initialize(self) -> None:
        """Initialize data manager."""
        try:
            if self._is_initialized:
                return

            # Get data paths from application config
            app_config = self._config_manager.get_config("application")
            data_paths = app_config.get("paths", {}).get("data", {})
            
            # Set up data directories
            self._run_path = Path(data_paths.get("runs", "data/runs"))
            self._parameter_path = Path(data_paths.get("parameters", "data/parameters"))
            self._pattern_path = Path(data_paths.get("patterns", "data/patterns"))
            self._sequence_path = Path(data_paths.get("sequences", "data/sequences"))
            
            # Create directories if they don't exist
            for path in [self._run_path, self._parameter_path, 
                        self._pattern_path, self._sequence_path]:
                path.mkdir(parents=True, exist_ok=True)
                
            # Create year directory for runs
            year = datetime.now().strftime("%Y")
            self._year_path = self._run_path / year
            self._year_path.mkdir(parents=True, exist_ok=True)
            
            # Subscribe to tag updates for data collection
            await self._message_broker.subscribe(
                "tag/update",
                self._handle_tag_update
            )
            
            self._is_initialized = True
            logger.info("Data manager initialization complete")
            
        except Exception as e:
            logger.exception("Failed to initialize data manager")
            raise OperationError(f"Data manager initialization failed: {str(e)}") from e

    async def shutdown(self) -> None:
        """Shutdown data manager."""
        try:
            # Save any pending data
            if self._process_data:
                await self.save_process_data("shutdown_save")
                
            self._is_initialized = False
            logger.info("Data manager shutdown complete")
            
        except Exception as e:
            logger.exception("Error during data manager shutdown")
            raise OperationError(f"Data manager shutdown failed: {str(e)}") from e

    async def set_user(self, username: str) -> None:
        """Set the current user for data collection."""
        try:
            self._current_user = username
            logger.debug(f"Current user set to: {username}")
            
            await self._message_broker.publish(
                "data/user/changed",
                {
                    "username": username,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting user: {e}")
            raise OperationError(f"Failed to set user: {str(e)}") from e

    async def set_cancelled(self, cancelled: bool = True) -> None:
        """Mark the current run as cancelled."""
        try:
            self._cancelled = cancelled
            logger.debug(f"Run marked as {'cancelled' if cancelled else 'not cancelled'}")
            
            await self._message_broker.publish(
                "data/run/status",
                {
                    "cancelled": cancelled,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error setting cancelled state: {e}")
            raise OperationError(f"Failed to set cancelled state: {str(e)}") from e

    def generate_filename(self, sequence_name: str) -> str:
        """Generate a filename for the process data."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_prefix = self._current_user or "unknown_user"
        cancelled_suffix = "_cancelled" if self._cancelled else ""
        return f"{user_prefix}_{sequence_name}_{timestamp}{cancelled_suffix}.json"

    async def _handle_tag_update(self, data: Dict[str, Any]) -> None:
        """Handle incoming process data from tag updates."""
        try:
            # Track spray events
            spray_active = False
            feeder_active = False
            pattern_active = False
            
            # Get tag and value from update
            tag = data.get("tag")
            value = data.get("value")
            timestamp = data.get("timestamp", datetime.now().isoformat())
            
            if tag and value is not None:
                # Collect process data for process.* and chamber.* tags
                if tag.startswith("process.") or tag.startswith("chamber."):
                    self._process_data[tag] = {
                        "value": value,
                        "timestamp": timestamp
                    }
                    
                    # Publish process status update
                    await self._message_broker.publish(
                        "process/status/data",
                        {
                            "data": {tag: value},
                            "timestamp": timestamp
                        }
                    )
                    
                # Track spray conditions
                if tag == "feeder.status":
                    feeder_active = value
                elif tag == "pattern.active":
                    pattern_active = value
                    
            # Check if this is a spray event
            spray_active = feeder_active and pattern_active
            if spray_active and not self._spray_active:
                # New spray started
                await self._record_spray_start()
            elif not spray_active and self._spray_active:
                # Spray ended
                await self._record_spray_end()
                
            self._spray_active = spray_active
                    
        except Exception as e:
            logger.error(f"Error handling tag update: {e}")
            await self._message_broker.publish(
                "data/collection/error",
                {
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _record_spray_start(self) -> None:
        """Record start of spray event."""
        try:
            # Get current parameters
            params = await self._message_broker.request(
                "parameters/get/current",
                {"timestamp": datetime.now().isoformat()}
            )
            
            # Get current pattern
            pattern = await self._message_broker.request(
                "patterns/get/current",
                {"timestamp": datetime.now().isoformat()}
            )
            
            # Record spray start
            spray_data = {
                "spray_index": self._get_next_spray_index(),
                "sequence_file": self._current_sequence,
                "material_type": params.get("powder", {}).get("type", ""),
                "pattern_name": pattern.get("name", ""),
                "operator": self._current_user,
                "start_time": datetime.now().isoformat(),
                "powder_size": params.get("powder", {}).get("size_range", ""),
                "powder_lot": params.get("powder", {}).get("lot_number", ""),
                "manufacturer": params.get("powder", {}).get("manufacturer", ""),
                "nozzle_type": params.get("hardware", {}).get("nozzle_type", ""),
                "nozzle_diameter": params.get("hardware", {}).get("nozzle_diameter", ""),
                "nozzle_serial": params.get("hardware", {}).get("nozzle_serial", ""),
                "chamber_pressure_start": self._process_data.get("process.chamber.pressure", {}).get("value", 0),
                "nozzle_pressure_start": self._process_data.get("process.nozzle.pressure", {}).get("value", 0),
                "main_flow": params.get("gas", {}).get("main_flow", 0),
                "feeder_flow": params.get("gas", {}).get("feeder_flow", 0),
                "feeder_frequency": params.get("powder", {}).get("feeder", {}).get("frequency", 0),
                "pattern_type": pattern.get("type", ""),
                "completed": False,
                "error": ""
            }
            
            self._current_spray = spray_data
            self._append_to_spray_history(spray_data)
            
        except Exception as e:
            logger.error(f"Error recording spray start: {e}")
            await self._message_broker.publish(
                "data/spray/error",
                {
                    "error": str(e),
                    "context": "spray_start",
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def _record_spray_end(self) -> None:
        """Record end of spray event."""
        try:
            if not self._current_spray:
                return
            
            # Update spray data
            self._current_spray.update({
                "end_time": datetime.now().isoformat(),
                "chamber_pressure_end": self._process_data.get("process.chamber.pressure", {}).get("value", 0),
                "nozzle_pressure_end": self._process_data.get("process.nozzle.pressure", {}).get("value", 0),
                "completed": True
            })
            
            # Update history file
            self._append_to_spray_history(self._current_spray)
            
            # Clear current spray
            self._current_spray = None
            
        except Exception as e:
            logger.error(f"Error recording spray end: {e}")
            await self._message_broker.publish(
                "data/spray/error",
                {
                    "error": str(e),
                    "context": "spray_end",
                    "timestamp": datetime.now().isoformat()
                }
            )

    def _append_to_spray_history(self, spray_data: Dict[str, Any]) -> None:
        """Append spray data to history CSV."""
        try:
            history_file = self._run_path / "spray_history.csv"
            
            # Create file with headers if it doesn't exist
            if not history_file.exists():
                headers = [
                    "spray_index", "sequence_file", "material_type", "pattern_name",
                    "operator", "start_time", "end_time", "powder_size", "powder_lot",
                    "manufacturer", "nozzle_type", "nozzle_diameter", "nozzle_serial",
                    "chamber_pressure_start", "chamber_pressure_end",
                    "nozzle_pressure_start", "nozzle_pressure_end", "main_flow",
                    "feeder_flow", "feeder_frequency", "pattern_type", "completed", "error"
                ]
                with open(history_file, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(headers)
            
            # Append spray data
            with open(history_file, 'a', newline='') as f:
                writer = csv.writer(f)
                writer.writerow([
                    spray_data[key] for key in [
                        "spray_index", "sequence_file", "material_type", "pattern_name",
                        "operator", "start_time", "end_time", "powder_size", "powder_lot",
                        "manufacturer", "nozzle_type", "nozzle_diameter", "nozzle_serial",
                        "chamber_pressure_start", "chamber_pressure_end",
                        "nozzle_pressure_start", "nozzle_pressure_end", "main_flow",
                        "feeder_flow", "feeder_frequency", "pattern_type", "completed", "error"
                    ]
                ])
                
        except Exception as e:
            logger.error(f"Error appending to spray history: {e}")
            raise OperationError(f"Failed to update spray history: {str(e)}") from e

    def _get_next_spray_index(self) -> int:
        """Get next spray index from history file."""
        try:
            history_file = self._run_path / "spray_history.csv"
            if not history_file.exists():
                return 1
            
            with open(history_file, 'r') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header
                return max((int(row[0]) for row in reader), default=0) + 1
            
        except Exception as e:
            logger.error(f"Error getting next spray index: {e}")
            return 1

    async def save_process_data(self, sequence_name: str) -> None:
        """Save collected process data to file."""
        try:
            # Create year directory
            year = datetime.now().strftime("%Y")
            year_dir = self._run_path / year
            year_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename with .yaml extension
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            user_prefix = self._current_user or "unknown_user"
            cancelled_suffix = "_cancelled" if self._cancelled else ""
            filename = f"{user_prefix}_{sequence_name}_{timestamp}{cancelled_suffix}.yaml"
            filepath = year_dir / filename

            # Format run data in YAML structure
            run_data = {
                "run": {
                    "metadata": {
                        "name": sequence_name,
                        "timestamp": datetime.now().isoformat(),
                        "operator": self._current_user,
                        "description": ""
                    },
                    "sequence": {
                        "name": sequence_name,
                        "version": "1.0"
                    },
                    "data": {
                        "equipment": {
                            "chamber_readings": [],
                            "motion_data": []
                        },
                        "events": []
                    },
                    "results": {
                        "completion": 100 if not self._cancelled else 0,
                        "duration": 0.0,
                        "errors": 0,
                        "warnings": 0
                    }
                }
            }

            # Add process data
            for tag, data in self._process_data.items():
                if tag.startswith("chamber."):
                    run_data["run"]["data"]["equipment"]["chamber_readings"].append({
                        "timestamp": data["timestamp"],
                        "pressure": data["value"]
                    })
                elif tag.startswith("motion."):
                    run_data["run"]["data"]["equipment"]["motion_data"].append({
                        "timestamp": data["timestamp"],
                        "position": data["value"] if isinstance(data["value"], list) else [data["value"], 0, 0]
                    })

            # Save as YAML
            with open(filepath, 'w') as f:
                yaml.safe_dump(run_data, f, sort_keys=False)
                
            logger.info(f"Process data saved to {filepath}")
            
            # Notify data saved
            await self._message_broker.publish(
                "data/saved",
                {
                    "filename": str(filepath),
                    "metadata": run_data["run"]["metadata"],
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Clear collected data and reset cancelled flag after saving
            self._process_data.clear()
            self._cancelled = False
            
        except Exception as e:
            logger.error(f"Error saving process data: {e}")
            await self._message_broker.publish(
                "data/save/error",
                {
                    "error": str(e),
                    "sequence_name": sequence_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to save process data: {str(e)}") from e

    async def load_process_data(self, filepath: Path) -> Dict[str, Any]:
        """Load process data from file."""
        try:
            if not filepath.exists():
                raise FileNotFoundError(f"Process data file not found: {filepath}")
                
            with open(filepath, 'r') as f:
                data = json.load(f)
                
            logger.info(f"Process data loaded from {filepath}")
            
            # Notify data loaded
            await self._message_broker.publish(
                "data/loaded",
                {
                    "filename": str(filepath),
                    "metadata": data.get("metadata", {}),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            return data
            
        except Exception as e:
            logger.error(f"Error loading process data: {e}")
            await self._message_broker.publish(
                "data/load/error",
                {
                    "error": str(e),
                    "filepath": str(filepath),
                    "timestamp": datetime.now().isoformat()
                }
            )
            raise OperationError(f"Failed to load process data: {str(e)}") from e

    def get_current_data(self) -> Dict[str, Any]:
        """Get current process data."""
        return self._process_data.copy()

    async def clear_data(self) -> None:
        """Clear collected process data."""
        try:
            self._process_data.clear()
            logger.debug("Process data cleared")
            
            await self._message_broker.publish(
                "data/cleared",
                {
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error clearing data: {e}")
            raise OperationError(f"Failed to clear data: {str(e)}") from e

    async def compress_data(self, run_id: str) -> None:
        """Compress run data to save space."""
        try:
            run_path = self._run_path / f"{run_id}.json"
            if not run_path.exists():
                raise OperationError(f"Run data not found: {run_id}")
            
            # Load data
            with open(run_path, 'r') as f:
                data = json.load(f)
            
            # Compress process data
            compressed_data = {
                "metadata": data["metadata"],
                "process_data": {}
            }
            
            for tag, values in data["process_data"].items():
                # Only keep values that changed
                unique_values = []
                last_value = None
                for entry in values:
                    if entry["value"] != last_value:
                        unique_values.append(entry)
                        last_value = entry["value"]
                compressed_data["process_data"][tag] = unique_values
            
            # Save compressed data
            compressed_path = self._run_path / f"{run_id}_compressed.json"
            with open(compressed_path, 'w') as f:
                json.dump(compressed_data, f)
            
            logger.info(f"Compressed run data saved to {compressed_path}")
            
            # Publish compression complete
            await self._message_broker.publish(
                "data/compressed",
                {
                    "run_id": run_id,
                    "original_size": run_path.stat().st_size,
                    "compressed_size": compressed_path.stat().st_size,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error compressing data: {e}")
            raise OperationError(f"Failed to compress data: {str(e)}") from e

    async def create_backup(self, backup_path: Path) -> None:
        """Create backup of all data directories."""
        try:
            # Create backup directory
            backup_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all data directories
            for src_path in [self._run_path, self._parameter_path, 
                            self._pattern_path, self._sequence_path]:
                dst_path = backup_path / src_path.name
                if src_path.exists():
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
            
            logger.info(f"Data backup created at {backup_path}")
            
            # Publish backup complete
            await self._message_broker.publish(
                "data/backup/complete",
                {
                    "backup_path": str(backup_path),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            raise OperationError(f"Failed to create backup: {str(e)}") from e

    async def save_parameters(self, name: str, parameters: Dict[str, Any]) -> None:
        """Save parameters to history."""
        try:
            # Save to parameter history file
            history_file = self._parameter_path / f"{name}.json"
            
            # Add metadata
            parameter_data = {
                "metadata": {
                    "name": name,
                    "timestamp": datetime.now().isoformat(),
                    "user": self._current_user
                },
                "parameters": parameters
            }
            
            # Save to file
            with open(history_file, 'w') as f:
                json.dump(parameter_data, f, indent=2)
                
            # Publish to parameter history
            await self._message_broker.publish(
                "parameters/history",
                {
                    "name": name,
                    "parameters": parameters,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"Parameters saved to history: {name}")
            
        except Exception as e:
            logger.error(f"Error saving parameters to history: {e}")
            raise OperationError(f"Failed to save parameters to history: {str(e)}") from e

    async def load_parameters(self, name: str) -> Dict[str, Any]:
        """Load parameters from history."""
        try:
            history_file = self._parameter_path / f"{name}.json"
            
            if not history_file.exists():
                raise FileNotFoundError(f"Parameter history not found: {name}")
            
            with open(history_file, 'r') as f:
                parameter_data = json.load(f)
                
            logger.info(f"Parameters loaded from history: {name}")
            
            return parameter_data["parameters"]
            
        except Exception as e:
            logger.error(f"Error loading parameters from history: {e}")
            raise OperationError(f"Failed to load parameters from history: {str(e)}") from e

    async def save_run_data(self, run_name: str, data: Dict[str, Any]) -> None:
        """Save run data to YAML file."""
        try:
            # Create year directory
            year = datetime.now().strftime("%Y")
            year_dir = self._run_path / year
            year_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate filename
            filename = f"{run_name}.yaml"
            filepath = year_dir / filename
            
            # Format run data
            run_data = {
                "run": {
                    "metadata": {
                        "name": run_name,
                        "timestamp": datetime.now().isoformat(),
                        "operator": self._current_user,
                        "description": data.get("description", "")
                    },
                    "sequence": data.get("sequence", {}),
                    "parameters": data.get("parameters", {}),
                    "patterns": data.get("patterns", {}),
                    "data": {
                        "equipment": {
                            "chamber_readings": [],
                            "motion_data": []
                        },
                        "events": []
                    },
                    "results": {
                        "completion": 0,
                        "duration": 0.0,
                        "errors": 0,
                        "warnings": 0
                    }
                }
            }
            
            # Save to file
            with open(filepath, 'w') as f:
                yaml.safe_dump(run_data, f, sort_keys=False)
                
            logger.info(f"Run data saved to {filepath}")
            
        except Exception as e:
            logger.error(f"Error saving run data: {e}")
            raise OperationError(f"Failed to save run data: {str(e)}") from e