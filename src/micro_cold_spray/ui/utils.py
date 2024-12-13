"""UI utility functions."""

import os
import asyncio
from datetime import datetime
import psutil
from loguru import logger

_start_time = datetime.now()
_last_log_position = 0


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
    log_file = "logs/micro_cold_spray.log"
    
    try:
        if not os.path.exists(log_file):
            return {
                "timestamp": datetime.now().isoformat(),
                "level": "WARNING",
                "service": "monitor",
                "message": "Log file not found"
            }

        file_size = os.path.getsize(log_file)
        
        if file_size < _last_log_position:
            _last_log_position = 0
            
        if file_size > _last_log_position:
            with open(log_file, 'r') as f:
                f.seek(_last_log_position)
                new_entry = f.readline().strip()
                _last_log_position = f.tell()
                
                try:
                    parts = new_entry.split('|')
                    return {
                        "timestamp": parts[0].strip(),
                        "level": parts[1].strip(),
                        "service": parts[2].split('-')[0].strip(),
                        "message": parts[2].split('-')[1].strip()
                    }
                except Exception as e:
                    logger.error(f"Failed to parse log entry: {e}")
                    return {
                        "timestamp": datetime.now().isoformat(),
                        "level": "ERROR",
                        "service": "monitor",
                        "message": f"Failed to parse log: {new_entry}"
                    }
        
        await asyncio.sleep(1)
        return None
        
    except Exception as e:
        logger.error(f"Error monitoring logs: {e}")
        return {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "service": "monitor",
            "message": f"Monitor error: {str(e)}"
        }


def get_log_entries(n: int = 100) -> list:
    """Get recent log entries.
    
    Args:
        n: Number of entries to return
        
    Returns:
        List of log entries
    """
    log_file = "logs/micro_cold_spray.log"
    entries = []
    if os.path.exists(log_file):
        with open(log_file) as f:
            entries = f.readlines()[-n:]
    return entries
