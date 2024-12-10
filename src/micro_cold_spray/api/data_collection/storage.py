"""Storage implementations for data collection."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from abc import ABC, abstractmethod
from pathlib import Path

logger = logging.getLogger(__name__)


class SprayDataStorage(ABC):
    """Abstract base class for spray data storage implementations."""
    
    @abstractmethod
    async def save_spray_event(self, event: "SprayEvent") -> None:
        """Save a spray event."""
        pass
    
    @abstractmethod
    async def update_spray_event(self, event: "SprayEvent") -> None:
        """Update an existing spray event."""
        pass
    
    @abstractmethod
    async def get_spray_events(self, sequence_id: str) -> List["SprayEvent"]:
        """Get all spray events for a sequence."""
        pass


class CSVSprayStorage(SprayDataStorage):
    """CSV implementation of spray data storage."""
    
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()
    
    def _ensure_file_exists(self) -> None:
        """Ensure CSV file exists with headers."""
        if not self.file_path.exists():
            headers = [
                "spray_index", "sequence_file", "material_type", "pattern_name",
                "start_time", "end_time", "chamber_pressure_start", "chamber_pressure_end",
                "nozzle_pressure_start", "nozzle_pressure_end", "main_flow",
                "feeder_flow", "feeder_frequency", "pattern_type", "completed", "error"
            ]
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w') as f:
                f.write(','.join(headers) + '\n')
    
    async def save_spray_event(self, event: "SprayEvent") -> None:
        """Save a spray event to CSV."""
        with open(self.file_path, 'a') as f:
            f.write(self._format_event(event) + '\n')
    
    async def update_spray_event(self, event: "SprayEvent") -> None:
        """Update an existing spray event in CSV."""
        # For CSV, we'll append a new line - in a real DB we'd update
        await self.save_spray_event(event)
    
    async def get_spray_events(self, sequence_id: str) -> List["SprayEvent"]:
        """Get all spray events for a sequence from CSV."""
        from .service import SprayEvent  # Import here to avoid circular dependency
        events = []
        with open(self.file_path, 'r') as f:
            # Skip header
            next(f)
            for line in f:
                event = self._parse_event(line)
                if event.sequence_id == sequence_id:
                    events.append(event)
        return events
    
    def _format_event(self, event: "SprayEvent") -> str:
        """Format spray event as CSV line."""
        return ','.join([
            str(event.spray_index),
            event.sequence_id,
            event.material_type,
            event.pattern_name,
            event.start_time.isoformat(),
            event.end_time.isoformat() if event.end_time else '',
            str(event.chamber_pressure_start or ''),
            str(event.chamber_pressure_end or ''),
            str(event.nozzle_pressure_start or ''),
            str(event.nozzle_pressure_end or ''),
            str(event.main_flow or ''),
            str(event.feeder_flow or ''),
            str(event.feeder_frequency or ''),
            str(event.pattern_type or ''),
            str(event.completed).upper(),
            str(event.error or '')
        ])
    
    def _parse_event(self, line: str) -> "SprayEvent":
        """Parse CSV line into spray event."""
        from .service import SprayEvent  # Import here to avoid circular dependency
        parts = line.strip().split(',')
        return SprayEvent(
            spray_index=int(parts[0]),
            sequence_id=parts[1],
            material_type=parts[2],
            pattern_name=parts[3],
            start_time=datetime.fromisoformat(parts[4]),
            end_time=datetime.fromisoformat(parts[5]) if parts[5] else None,
            chamber_pressure_start=float(parts[6]) if parts[6] else None,
            chamber_pressure_end=float(parts[7]) if parts[7] else None,
            nozzle_pressure_start=float(parts[8]) if parts[8] else None,
            nozzle_pressure_end=float(parts[9]) if parts[9] else None,
            main_flow=float(parts[10]) if parts[10] else None,
            feeder_flow=float(parts[11]) if parts[11] else None,
            feeder_frequency=float(parts[12]) if parts[12] else None,
            pattern_type=parts[13] if parts[13] else None,
            completed=parts[14].upper() == 'TRUE',
            error=parts[15] if parts[15] else None
        )


class TimescaleDBStorage(SprayDataStorage):
    """TimescaleDB implementation of spray data storage."""
    
    def __init__(self, dsn: str):
        """Initialize TimescaleDB storage."""
        self._dsn = dsn
        
    async def save_spray_event(self, event: "SprayEvent") -> None:
        """Save a spray event."""
        logger.info(f"Saving spray event {event.spray_index} for sequence {event.sequence_id}")
            
    async def update_spray_event(self, event: "SprayEvent") -> None:
        """Update an existing spray event."""
        logger.info(f"Updating spray event {event.spray_index} for sequence {event.sequence_id}")
            
    async def get_spray_events(self, sequence_id: str) -> List["SprayEvent"]:
        """Get all spray events for a sequence."""
        logger.info(f"Getting spray events for sequence {sequence_id}")
        return [] 