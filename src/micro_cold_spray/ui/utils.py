"""UI utility functions."""

import os
from datetime import datetime
import psutil
from loguru import logger
from pathlib import Path
import aiofiles
from typing import List

_start_time = datetime.now()
_last_log_position = 0
LOG_FILE = Path("logs/micro_cold_spray.log")


def get_uptime() -> float:
    """Get service uptime in seconds."""
    return (datetime.now() - _start_time).total_seconds()


def get_memory_usage() -> int:
    """Get current memory usage in bytes."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss


async def monitor_service_logs() -> dict:
    """Monitor log file for new entries.
    
    Returns:
        Dict containing log entry data
    """
    global _last_log_position
    
    try:
        if not LOG_FILE.exists():
            return {
                "timestamp": datetime.now().isoformat(),
                "level": "WARNING",
                "service": "monitor",
                "message": "Log file not found"
            }

        # Check file permissions
        if not os.access(LOG_FILE, os.R_OK):
            return {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "service": "monitor",
                "message": "Permission denied accessing log file"
            }

        try:
            file_size = LOG_FILE.stat().st_size
        except PermissionError:
            return {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR",
                "service": "monitor",
                "message": "Permission denied accessing log file"
            }

        if file_size < _last_log_position:
            _last_log_position = 0
            
        if file_size > _last_log_position:
            try:
                with open(LOG_FILE, 'r') as f:
                    f.seek(_last_log_position)
                    new_entry = f.readline().strip()
                    _last_log_position = f.tell()
                    
                    try:
                        # Parse log entry
                        parts = [p.strip() for p in new_entry.split('|')]
                        if len(parts) != 3:
                            raise ValueError("Invalid log format")
                            
                        message_parts = parts[2].split('-', 1)
                        if len(message_parts) != 2:
                            raise ValueError("Invalid message format")
                            
                        return {
                            "timestamp": parts[0],
                            "level": parts[1],
                            "service": message_parts[0].strip(),
                            "message": message_parts[1].strip()
                        }
                    except Exception as e:
                        logger.error(f"Failed to parse log entry: {e}")
                        return {
                            "timestamp": datetime.now().isoformat(),
                            "level": "ERROR",
                            "service": "monitor",
                            "message": f"Failed to parse log: {new_entry}"
                        }
            except PermissionError:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "service": "monitor",
                    "message": "Permission denied accessing log file"
                }
            except Exception as e:
                logger.error(f"Error monitoring logs: {e}")
                return {
                    "timestamp": datetime.now().isoformat(),
                    "level": "ERROR",
                    "service": "monitor",
                    "message": f"Monitor error: {str(e)}"
                }

    except Exception as e:
        logger.error(f"Error monitoring logs: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "service": "monitor",
            "message": f"Monitor error: {str(e)}"
        }

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
