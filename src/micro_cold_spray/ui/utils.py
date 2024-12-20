"""UI utility functions."""

import os
from datetime import datetime
import psutil
from loguru import logger
from pathlib import Path
import aiofiles
from typing import Dict, Optional, Any, List

_start_time = datetime.now()
_last_log_position = 0
LOG_FILE = Path("logs/micro_cold_spray.log")


def get_uptime() -> float:
    """Get service uptime in seconds."""
    return (datetime.now() - _start_time).total_seconds()


def get_memory_usage() -> Dict[str, float]:
    """Get current memory usage statistics.
    
    Returns:
        Dict containing memory usage in MB:
            - total: Total memory allocated
            - used: Currently used memory
            - percent: Percentage used
    """
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        
        total_mb = mem_info.rss / (1024 * 1024)  # Convert to MB
        used_mb = mem_info.vms / (1024 * 1024)
        percent = (used_mb / total_mb) * 100 if total_mb > 0 else 0
        
        return {
            "total": round(total_mb, 2),
            "used": round(used_mb, 2),
            "percent": round(percent, 1)
        }
    except Exception as e:
        logger.error(f"Error getting memory usage: {e}")
        return {
            "total": 0.0,
            "used": 0.0,
            "percent": 0.0
        }


async def monitor_service_logs() -> Optional[Dict[str, Any]]:
    """Monitor log file for new entries.
    
    Returns:
        Dict containing log entry data or None if no new entries
    """
    global _last_log_position
    
    try:
        if not LOG_FILE.exists():
            logger.warning("Log file not found")
            return None

        if not os.access(LOG_FILE, os.R_OK):
            logger.error("Permission denied accessing log file")
            return None

        try:
            file_size = LOG_FILE.stat().st_size
        except OSError as e:
            logger.error(f"Error accessing log file: {e}")
            return None

        # Handle log rotation
        if file_size < _last_log_position:
            _last_log_position = 0
            
        if file_size > _last_log_position:
            try:
                async with aiofiles.open(LOG_FILE, 'r') as f:
                    await f.seek(_last_log_position)
                    new_entry = await f.readline()
                    if not new_entry:  # Empty line
                        return None
                        
                    _last_log_position = await f.tell()
                    
                    # Parse log entry
                    try:
                        parts = [p.strip() for p in new_entry.split('|')]
                        if len(parts) != 3:
                            logger.warning(f"Invalid log format: {new_entry}")
                            return None
                            
                        message_parts = parts[2].split('-', 1)
                        if len(message_parts) != 2:
                            logger.warning(f"Invalid message format: {parts[2]}")
                            return None
                            
                        return {
                            "timestamp": parts[0],
                            "level": parts[1].strip(),
                            "service": message_parts[0].strip(),
                            "message": message_parts[1].strip()
                        }
                    except Exception as e:
                        logger.error(f"Failed to parse log entry: {e}")
                        return None
                        
            except OSError as e:
                logger.error(f"Error reading log file: {e}")
                return None

    except Exception as e:
        logger.error(f"Error monitoring logs: {e}")
        return None

    return None


async def get_log_entries(n: int = 100) -> List[str]:
    """Get the last n log entries.
    
    Args:
        n: Number of entries to retrieve
        
    Returns:
        List of log entries
    """
    try:
        file_path = LOG_FILE
        if not file_path.exists():
            return []

        if not os.access(file_path, os.R_OK):
            return ["Permission denied while reading log file"]

        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                lines = content.splitlines()
                return lines[-n:]
        except PermissionError:
            return ["Permission denied while reading log file"]
        except OSError as e:
            return [f"Error reading log file: {str(e)}"]
        except Exception as e:
            logger.error(f"Error reading log file: {e}")
            return [f"Error reading log file: {str(e)}"]
    except Exception as e:
        logger.error(f"Error accessing log file: {e}")
        return [f"Error accessing log file: {str(e)}"]
