"""Service for managing data collection operations."""

import asyncio
import logging
import yaml
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from ..base import BaseService
from ...core.infrastructure.messaging.message_broker import MessageBroker
from ...core.infrastructure.config.config_manager import ConfigManager
from .storage import SprayDataStorage, CSVSprayStorage, TimescaleDBStorage

logger = logging.getLogger(__name__)


class DataCollectionError(Exception):
    """Base exception for data collection errors."""
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


@dataclass
class SprayEvent:
    """Represents a single spray event during sequence execution."""
    sequence_id: str
    spray_index: int
    material_type: str
    pattern_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    chamber_pressure_start: Optional[float] = None
    chamber_pressure_end: Optional[float] = None
    nozzle_pressure_start: Optional[float] = None
    nozzle_pressure_end: Optional[float] = None
    main_flow: Optional[float] = None
    feeder_flow: Optional[float] = None
    feeder_frequency: Optional[float] = None
    pattern_type: Optional[str] = None
    completed: bool = False
    error: Optional[str] = None


@dataclass
class CollectionSession:
    """Represents an active data collection session."""
    sequence_id: str
    start_time: datetime
    run_name: str
    sequence_data: Dict[str, Any]
    collection_params: Dict[str, Any]
    current_spray: Optional[SprayEvent] = None
    spray_events: List[SprayEvent] = None


class DataCollectionService(BaseService):
    """Service for managing data collection operations."""
    
    STORAGE_TYPES = {
        "csv": CSVSprayStorage,
        "timescaledb": TimescaleDBStorage
    }
    
    def __init__(
        self,
        message_broker: MessageBroker,
        config_manager: ConfigManager
    ):
        super().__init__()
        self._message_broker = message_broker
        self._config_manager = config_manager
        self._active_session: Optional[CollectionSession] = None
        self._collection_ready = asyncio.Event()
        self._data_root: Optional[Path] = None
        self._runs_path: Optional[Path] = None
        self._sequences_path: Optional[Path] = None
        self._spray_storage: Optional[SprayDataStorage] = None
        
    async def start(self) -> None:
        """Initialize the service."""
        await super().start()
        
        # Get data paths from application config
        app_config = await self._config_manager.get_config("application")
        data_paths = app_config.get("paths", {}).get("data", {})
        
        # Set up data directories
        self._data_root = Path(data_paths.get("root", "data"))
        self._runs_path = Path(data_paths.get("runs", "data/runs"))
        self._sequences_path = Path(data_paths.get("sequences", "data/sequences"))
        
        # Initialize spray data storage based on config
        storage_config = app_config.get("data_collection", {}).get("storage", {})
        storage_type = storage_config.get("type", "csv")
        
        if storage_type not in self.STORAGE_TYPES:
            raise ValueError(f"Unsupported storage type: {storage_type}")
            
        storage_class = self.STORAGE_TYPES[storage_type]
        
        if storage_type == "csv":
            spray_history_path = self._data_root / "runs" / "spray_history.csv"
            self._spray_storage = storage_class(spray_history_path)
        elif storage_type == "timescaledb":
            dsn = storage_config.get("dsn")
            if not dsn:
                raise ValueError("TimescaleDB DSN not configured")
            self._spray_storage = storage_class(dsn)
        
        # Create directories
        self._runs_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using runs directory: {self._runs_path}")
        logger.info(f"Using storage backend: {storage_type}")
        
    async def stop(self) -> None:
        """Stop the service."""
        if self._spray_storage and hasattr(self._spray_storage, 'cleanup'):
            await self._spray_storage.cleanup()
        await super().stop()
        
    @property
    def is_collecting(self) -> bool:
        """Check if data collection is active."""
        return self._active_session is not None
        
    @property
    def active_session(self) -> Optional[CollectionSession]:
        """Get current collection session if any."""
        return self._active_session
        
    async def start_collection(self, sequence_id: str, collection_params: Dict[str, Any]) -> None:
        """Start data collection for a sequence."""
        if self.is_collecting:
            raise DataCollectionError(
                "Data collection already in progress",
                {"active_sequence": self._active_session.sequence_id}
            )
            
        try:
            # Load sequence data
            sequence_path = self._sequences_path / f"{sequence_id}.yaml"
            if not sequence_path.exists():
                raise DataCollectionError(
                    f"Sequence file not found: {sequence_id}",
                    {"path": str(sequence_path)}
                )
                
            with open(sequence_path, 'r') as f:
                sequence_data = yaml.safe_load(f)
            
            # Generate run name and create run file
            run_name = f"{sequence_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            run_data = {
                "metadata": {
                    "name": run_name,
                    "sequence_id": sequence_id,
                    "start_time": datetime.now().isoformat(),
                    "status": "running"
                },
                "sequence": sequence_data,
                "collection": collection_params
            }
            
            # Save run file
            run_path = self._runs_path / f"{run_name}.yaml"
            with open(run_path, 'w') as f:
                yaml.dump(run_data, f, sort_keys=False)
            
            # Initialize collection session
            self._active_session = CollectionSession(
                sequence_id=sequence_id,
                start_time=datetime.now(),
                run_name=run_name,
                sequence_data=sequence_data,
                collection_params=collection_params,
                spray_events=[]
            )
            
            # Notify collection started
            await self._message_broker.publish(
                "data_collection/state",
                {
                    "state": "started",
                    "sequence_id": sequence_id,
                    "run_name": run_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Signal collection is ready
            self._collection_ready.set()
            
            logger.info(f"Started data collection for sequence {sequence_id}")
            
        except Exception as e:
            raise DataCollectionError(
                f"Failed to start data collection: {str(e)}"
            )
    
    async def start_spray_event(
        self,
        material_type: str,
        pattern_name: str,
        pattern_type: str,
        params: Dict[str, Any]
    ) -> None:
        """Start recording a spray event."""
        if not self.is_collecting:
            raise DataCollectionError("No active collection session")
            
        session = self._active_session
        
        # Create new spray event
        spray_index = len(session.spray_events) + 1
        event = SprayEvent(
            sequence_id=session.sequence_id,
            spray_index=spray_index,
            material_type=material_type,
            pattern_name=pattern_name,
            pattern_type=pattern_type,
            start_time=datetime.now(),
            **params
        )
        
        # Save initial event
        await self._spray_storage.save_spray_event(event)
        
        # Update session
        session.current_spray = event
        session.spray_events.append(event)
        
        # Notify spray started
        await self._message_broker.publish(
            "data_collection/spray",
            {
                "state": "started",
                "sequence_id": session.sequence_id,
                "spray_index": spray_index,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    async def end_spray_event(self, params: Dict[str, Any], error: Optional[str] = None) -> None:
        """End recording current spray event."""
        if not self.is_collecting or not self._active_session.current_spray:
            raise DataCollectionError("No active spray event")
            
        session = self._active_session
        event = session.current_spray
        
        # Update event
        event.end_time = datetime.now()
        event.completed = error is None
        event.error = error
        for key, value in params.items():
            setattr(event, key, value)
        
        # Save updated event
        await self._spray_storage.update_spray_event(event)
        
        # Clear current spray
        session.current_spray = None
        
        # Notify spray ended
        await self._message_broker.publish(
            "data_collection/spray",
            {
                "state": "ended",
                "sequence_id": session.sequence_id,
                "spray_index": event.spray_index,
                "completed": event.completed,
                "error": error,
                "timestamp": datetime.now().isoformat()
            }
        )
            
    async def stop_collection(self) -> None:
        """Stop current data collection."""
        if not self.is_collecting:
            logger.warning("No active data collection to stop")
            return
            
        try:
            session = self._active_session
            
            # End any active spray event
            if session.current_spray:
                await self.end_spray_event(
                    params={},
                    error="Collection stopped before spray completion"
                )
            
            # Load current run file
            run_path = self._runs_path / f"{session.run_name}.yaml"
            with open(run_path, 'r') as f:
                run_data = yaml.safe_load(f)
            
            # Update run file
            run_data["metadata"]["end_time"] = datetime.now().isoformat()
            run_data["metadata"]["status"] = "completed"
            run_data["spray_events"] = [
                {
                    "spray_index": event.spray_index,
                    "start_time": event.start_time.isoformat(),
                    "end_time": event.end_time.isoformat() if event.end_time else None,
                    "completed": event.completed,
                    "error": event.error
                }
                for event in session.spray_events
            ]
            
            # Save updated run file
            with open(run_path, 'w') as f:
                yaml.dump(run_data, f, sort_keys=False)
            
            # Notify collection stopped
            await self._message_broker.publish(
                "data_collection/state",
                {
                    "state": "stopped",
                    "sequence_id": session.sequence_id,
                    "run_name": session.run_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # Clean up session
            self._active_session = None
            self._collection_ready.clear()
            
            logger.info(f"Stopped data collection for sequence {session.sequence_id}")
            
        except Exception as e:
            raise DataCollectionError(
                f"Failed to stop data collection: {str(e)}"
            )
            
    async def cleanup(self) -> None:
        """Clean up any active collection on service shutdown."""
        if self.is_collecting:
            await self.stop_collection() 