"""Tests for UI utilities."""

import pytest
import asyncio
from unittest.mock import patch
from micro_cold_spray.ui.utils import (
    get_uptime,
    get_memory_usage,
    monitor_service_logs,
    get_log_entries
)


class MockAsyncContextManager:
    """Mock async context manager for testing."""
    def __init__(self, error=None, content=""):
        self.error = error
        self.content = content

    async def __aenter__(self):
        if self.error:
            raise self.error
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def read(self):
        return self.content


@pytest.fixture(scope="function")
async def event_loop():
    """Create an event loop for each test."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    # Clean up pending tasks
    pending = asyncio.all_tasks(loop)
    for task in pending:
        task.cancel()
    if pending:
        await asyncio.gather(*pending, return_exceptions=True)
    await loop.shutdown_asyncgens()
    loop.close()


class TestUtils:
    """Test UI utility functions."""
    
    @pytest.mark.asyncio
    async def test_get_uptime(self):
        """Test uptime calculation."""
        uptime = get_uptime()
        assert isinstance(uptime, float)
        assert uptime >= 0
        
    @pytest.mark.asyncio
    async def test_get_memory_usage(self):
        """Test memory usage retrieval."""
        memory = get_memory_usage()
        assert isinstance(memory, int)
        assert memory > 0
        
    @pytest.mark.asyncio
    async def test_get_log_entries_error(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval with file error."""
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        log_file.write_text("Test log")

        def mock_access(path, mode):
            return False
        monkeypatch.setattr('os.access', mock_access)

        def mock_aiofiles_open(*args, **kwargs):
            return MockAsyncContextManager(error=PermissionError("Permission denied"))
        monkeypatch.setattr('aiofiles.open', mock_aiofiles_open)

        entries = await get_log_entries(n=10)
        assert entries == ["Permission denied while reading log file"]

    @pytest.mark.asyncio
    async def test_get_log_entries_read_error(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval with read error."""
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        log_file.write_text("Test log")

        def mock_aiofiles_open(*args, **kwargs):
            return MockAsyncContextManager(error=OSError("Read error"))
        monkeypatch.setattr('aiofiles.open', mock_aiofiles_open)

        entries = await get_log_entries(n=10)
        assert entries == ["Error reading log file: Read error"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_permission_error_with_mocks(self, tmp_path):
        """Test log monitoring with permission error using mocks."""
        log_file = tmp_path / "test.log"
        log_file.write_text("Test log entry")

        with patch('os.stat', side_effect=PermissionError("Permission denied")), \
             patch('os.path.exists', return_value=True), \
             patch('micro_cold_spray.ui.utils.LOG_FILE', log_file):

            log_entry = await monitor_service_logs()
            assert log_entry is not None
            assert log_entry["level"] == "ERROR"
            assert "Permission denied" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs(self, temp_log_dir, monkeypatch):
        """Test log monitoring."""
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "micro_cold_spray.log")
        monkeypatch.setattr('micro_cold_spray.ui.utils._last_log_position', 0)
        
        log_file = temp_log_dir / "micro_cold_spray.log"
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["service"] == "test_service"
        assert log_entry["message"] == "Test message"

    @pytest.mark.asyncio
    async def test_get_log_entries(self, temp_log_dir, monkeypatch):
        """Test log entry retrieval."""
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "micro_cold_spray.log")

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
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "nonexistent.log")
        entries = await get_log_entries(n=2)
        assert entries == []

    @pytest.mark.asyncio
    async def test_monitor_service_logs_no_file(self, temp_log_dir, monkeypatch):
        """Test log monitoring with missing file."""
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', temp_log_dir / "nonexistent.log")
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "WARNING"
        assert "Log file not found" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_invalid_format(self, temp_log_dir, monkeypatch):
        """Test log monitoring with invalid format."""
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        log_file.write_text("Invalid log format")
        
        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Failed to parse log" in log_entry["message"]

    @pytest.mark.asyncio
    async def test_monitor_service_logs_file_error(self, temp_log_dir, monkeypatch):
        """Test log monitoring with file read error."""
        log_file = temp_log_dir / "micro_cold_spray.log"
        monkeypatch.setattr('micro_cold_spray.ui.utils.LOG_FILE', log_file)
        log_file.write_text("2024-01-01 12:00:00 | INFO | test_service - Test message")

        def mock_access(path, mode):
            return False
        monkeypatch.setattr('os.access', mock_access)

        log_entry = await monitor_service_logs()
        assert log_entry is not None
        assert log_entry["level"] == "ERROR"
        assert "Permission denied" in log_entry["message"]
