"""Tests for UI utilities."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from micro_cold_spray.ui.utils import (
    get_uptime,
    get_memory_usage,
    monitor_service_logs,
    get_log_entries
)
from unittest.mock import patch


@pytest.fixture
def mock_path_with_stat_error(temp_log_dir):
    """Create a Path object that raises PermissionError on stat."""
    path = temp_log_dir / "micro_cold_spray.log"
    path.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
    
    # Create a mock stat method that raises PermissionError
    mock_stat = MagicMock(side_effect=PermissionError("Permission denied"))
    
    # Create a new Path object with the mocked stat method
    mock_path = MagicMock(spec=Path)
    mock_path.__str__.return_value = str(path)
    mock_path.exists.return_value = True
    mock_path.stat = mock_stat
    
    return mock_path


class TestUtils:
    """Test UI utility functions."""
    
    def test_get_uptime(self):
        """Test uptime calculation."""
        uptime = get_uptime()
        assert isinstance(uptime, float)
        assert uptime >= 0
        
    def test_get_memory_usage(self):
        """Test memory usage retrieval."""
        memory = get_memory_usage()
        assert isinstance(memory, int)
        assert memory > 0
        
    @pytest.mark.asyncio
    async def test_monitor_service_logs(self, temp_log_dir, monkeypatch):
        """Test log monitoring."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "micro_cold_spray.log")
        monkeypatch.setattr('micro_cold_spray.ui.utils._last_log_position', 0)
        
        log_file = temp_log_dir / "micro_cold_spray.log"
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        # Monitor logs
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["service"] == "test_service"
        assert log_entry["message"] == "Test message"
        
    @pytest.mark.asyncio
    async def test_get_log_entries(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "micro_cold_spray.log")

        # Write test logs
        log_file = temp_log_dir / "micro_cold_spray.log"
        log_file.write_text("\n".join([
            "2024-01-01 12:00:00 | INFO | test_service - Message 1",
            "2024-01-01 12:00:01 | INFO | test_service - Message 2"
        ]))

        entries = await get_log_entries(n=2)
        assert len(entries) == 2
        assert entries[0].endswith("Message 1")
        assert entries[1].endswith("Message 2")

    @pytest.mark.asyncio
    async def test_get_log_entries_no_file(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval with no file."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "nonexistent.log")
        entries = await get_log_entries(n=2)
        assert entries == []

    @pytest.mark.asyncio
    async def test_get_log_entries_error(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval with file error."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)

        # Create log file
        log_file.write_text("Test log")

        # Mock os.access to simulate permission error
        def mock_access(path, mode):
            return False
        monkeypatch.setattr('os.access', mock_access)

        # Mock aiofiles.open to raise PermissionError
        async def mock_aiofiles_open(*args, **kwargs):
            raise PermissionError("Permission denied")
        monkeypatch.setattr('aiofiles.open', mock_aiofiles_open)

        entries = await get_log_entries(n=10)
        assert entries == ["Permission denied while reading log file"]

    @pytest.mark.asyncio
    async def test_get_log_entries_read_error(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval with read error."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)

        # Create log file
        log_file.write_text("Test log")

        # Mock aiofiles.open to raise OSError
        async def mock_aiofiles_open(*args, **kwargs):
            raise OSError("Read error")
        monkeypatch.setattr('aiofiles.open', mock_aiofiles_open)

        entries = await get_log_entries(n=10)
        assert entries == ["Error reading log file: Read error"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_no_file(self, temp_log_dir, monkeypatch):
        """Test log monitoring with missing file."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "nonexistent.log")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "WARNING"
        assert "Log file not found" in log_entry["message"]
        
    @pytest.mark.asyncio
    async def test_monitor_service_logs_invalid_format(self, temp_log_dir, monkeypatch):
        """Test log monitoring with invalid format."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "micro_cold_spray.log")
        
        log_file = temp_log_dir / "micro_cold_spray.log"
        log_file.write_text("Invalid log format")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Failed to parse log" in log_entry["message"]
        
    @pytest.mark.asyncio
    async def test_monitor_service_logs_file_error(self, temp_log_dir, monkeypatch):
        """Test log monitoring with file read error."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        # Mock os.access to simulate permission error
        def mock_access(path, mode):
            return False
        monkeypatch.setattr('os.access', mock_access)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Permission denied" in log_entry["message"]
        
    @pytest.mark.asyncio
    async def test_monitor_service_logs_stat_error(self, temp_log_dir, monkeypatch):
        """Test log monitoring with stat error."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        # Mock Path.stat to raise an error
        def mock_stat(*args, **kwargs):
            raise OSError("Stat error")
        monkeypatch.setattr(Path, 'stat', mock_stat)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Monitor error" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_file_size_reset(self, temp_log_dir, monkeypatch):
        """Test log monitoring with file size reset."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        monkeypatch.setattr('micro_cold_spray.ui.utils._last_log_position', 100)  # Set larger than file size
        
        # Create log file
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["service"] == "test_service"
        assert log_entry["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_monitor_service_logs_no_new_entries(self, temp_log_dir, monkeypatch):
        """Test log monitoring with no new entries."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file
        content = "2024-01-01 12:00:00 | INFO | test_service - Test message"
        log_file.write_text(content)
        monkeypatch.setattr('micro_cold_spray.ui.utils._last_log_position', len(content))
        
        log_entry = await monitor_service_logs()
        assert log_entry is None

    @pytest.mark.asyncio
    async def test_monitor_service_logs_invalid_message_format(self, temp_log_dir, monkeypatch):
        """Test log monitoring with invalid message format."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file with invalid message format (missing dash)
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service Test message")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Failed to parse log" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_permission_error_stat(self, temp_log_dir, monkeypatch):
        """Test log monitoring with permission error during stat."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        # Mock Path.stat to raise PermissionError
        def mock_stat(*args, **kwargs):
            raise PermissionError("Permission denied")
        monkeypatch.setattr(Path, 'stat', mock_stat)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Permission denied" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_permission_error_read(self, temp_log_dir, monkeypatch):
        """Test log monitoring with permission error during read."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Create log file
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        # Mock open to raise PermissionError
        def mock_open(*args, **kwargs):
            raise PermissionError("Permission denied")
        monkeypatch.setattr('builtins.open', mock_open)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Permission denied" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_general_exception(self, temp_log_dir, monkeypatch):
        """Test log monitoring with general exception."""
        # Mock log file path
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        
        # Mock Path.exists to raise an unexpected error
        def mock_exists(*args, **kwargs):
            raise Exception("Unexpected error")
        monkeypatch.setattr(Path, 'exists', mock_exists)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Monitor error" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_permission_error_stat_specific(self, mock_path_with_stat_error, monkeypatch):
        """Test log monitoring with specific PermissionError during stat."""
        # Mock log file path
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', mock_path_with_stat_error)
        
        # Mock os.access to allow access
        def mock_access(path, mode):
            return True
        monkeypatch.setattr('os.access', mock_access)
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Permission denied" in log_entry["message"]
        assert log_entry["service"] == "monitor"

    @pytest.mark.asyncio
    async def test_get_log_entries_permission_error_specific(self, tmp_path):
        """Test get_log_entries with permission error."""
        # Create a test log file
        log_file = tmp_path / "test.log"
        log_file.write_text("Test log entry")

        # Mock os.stat to raise PermissionError
        def mock_stat(*args, **kwargs):
            raise PermissionError("Permission denied")

        # Mock os.path.exists to return True
        def mock_exists(*args, **kwargs):
            return True

        # Mock aiofiles.open to raise PermissionError
        async def mock_aiofiles_open(*args, **kwargs):
            raise PermissionError("Permission denied")

        with patch('os.stat', side_effect=mock_stat), \
             patch('os.path.exists', side_effect=mock_exists), \
             patch('aiofiles.open', side_effect=mock_aiofiles_open):

            # Call get_log_entries and verify it handles the error
            entries = await get_log_entries(log_file)
            assert entries == ["Permission denied while reading log file"]
