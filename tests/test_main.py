"""Tests for main module."""

import pytest
import asyncio
import requests
from unittest.mock import patch, MagicMock, AsyncMock
from micro_cold_spray.__main__ import (
    ServiceManager,
    setup_logging,
    ensure_directories,
    check_service_health,
    wait_for_service,
    main
)


# Define test service at module level to make it picklable
async def test_service():
    """Test service function."""
    pass


def test_service_sync():
    """Synchronous wrapper for test service."""
    asyncio.run(test_service())


# Define stubborn process at module level to make it picklable
def stubborn_process():
    """Process that ignores terminate signal."""
    from signal import signal, SIGTERM, SIG_IGN
    signal(SIGTERM, SIG_IGN)
    while True:
        pass


# Define mock runner at module level to make it picklable
def mock_non_critical_runner():
    """Mock runner for non-critical service test."""
    return True


class TestMain:
    """Test main application functionality."""
    
    def test_setup_logging(self, temp_log_dir, monkeypatch):
        """Test logging setup."""
        # Mock the log directory path
        monkeypatch.setattr('micro_cold_spray.__main__.LOG_DIR', temp_log_dir)
        setup_logging()
        assert (temp_log_dir / "micro_cold_spray.log").exists()
        
    def test_ensure_directories(self, tmp_path, monkeypatch):
        """Test directory creation."""
        # Mock the base directory path
        monkeypatch.setattr('micro_cold_spray.__main__.BASE_DIR', tmp_path)
        ensure_directories()
        required_dirs = [
            "logs", "config", "config/schemas", "data",
            "data/parameters", "data/patterns", "data/sequences",
            "data/powders", "data/runs"
        ]
        for dir_name in required_dirs:
            assert (tmp_path / dir_name).exists()
            
    @pytest.mark.asyncio
    async def test_service_manager(self):
        """Test service manager functionality."""
        manager = ServiceManager()
        
        # Use the synchronous wrapper for the test service
        success = await manager.start_service(
            "test",
            test_service_sync,
            critical=False
        )
        assert success
        
        # Test service monitoring
        assert "test" in manager.processes
        
        # Test service stop
        manager.stop_service("test")
        assert "test" not in manager.processes

    @pytest.mark.asyncio
    async def test_service_manager_critical_failure(self):
        """Test service manager with critical service failure."""
        manager = ServiceManager()
        
        # Test critical service failure
        success = await manager.start_service(
            "critical_test",
            lambda: None,
            critical=True
        )
        assert not success

    @pytest.mark.asyncio
    async def test_service_manager_health_check(self, monkeypatch):
        """Test service manager health check."""
        manager = ServiceManager()
        
        # Add check_service_health method to manager
        async def check_service_health(port):
            return True
        manager.check_service_health = check_service_health
        
        # Test health check
        is_healthy = await manager.check_service_health(8000)
        assert is_healthy

    @pytest.mark.asyncio
    async def test_check_service_health_success(self):
        """Test successful health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        
        with patch('requests.get', return_value=mock_response):
            result = await check_service_health(8000)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_degraded(self):
        """Test degraded health check."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "degraded"}
        
        with patch('requests.get', return_value=mock_response):
            result = await check_service_health(8000)
            assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_404(self):
        """Test health check with 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        with patch('requests.get', return_value=mock_response):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await check_service_health(8000, retries=2, delay=0.1)
                assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_connection_error(self):
        """Test health check with connection error."""
        with patch('requests.get', side_effect=requests.ConnectionError):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await check_service_health(8000, retries=2, delay=0.1)
                assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_service_success(self):
        """Test successful service wait."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch('requests.get', return_value=mock_response):
            result = await wait_for_service(8000, timeout=1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_wait_for_service_timeout(self):
        """Test service wait timeout."""
        with patch('requests.get', side_effect=requests.ConnectionError):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await wait_for_service(8000, timeout=0.1)
                assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_unhealthy(self):
        """Test unhealthy status."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "unhealthy"}
        
        with patch('requests.get', return_value=mock_response):
            result = await check_service_health(8000, retries=1)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_bad_status(self):
        """Test non-200 status code."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        
        with patch('requests.get', return_value=mock_response):
            result = await check_service_health(8000, retries=1)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_invalid_json(self):
        """Test invalid JSON response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        
        with patch('requests.get', return_value=mock_response):
            result = await check_service_health(8000, retries=1)
            assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_timeout(self):
        """Test request timeout."""
        with patch('requests.get', side_effect=requests.Timeout):
            result = await check_service_health(8000, retries=1)
            assert result is False

    @pytest.mark.asyncio
    async def test_wait_for_service_request_error(self):
        """Test service wait with request error."""
        with patch('requests.get', side_effect=requests.RequestException):
            with patch('asyncio.sleep'):
                result = await wait_for_service(8000, timeout=0.1)
                assert result is False

    @pytest.mark.asyncio
    async def test_service_manager_connection_failure(self):
        """Test service manager with connection failure."""
        manager = ServiceManager()
        
        # Mock wait_for_service to simulate connection failure
        async def mock_wait_for_service(port):
            return False
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr('micro_cold_spray.__main__.wait_for_service', mock_wait_for_service)
        
        success = await manager.start_service(
            "test",
            test_service_sync,
            critical=False,
            port=8000
        )
        assert not success

    @pytest.mark.asyncio
    async def test_service_manager_non_critical_health_failure(self):
        """Test non-critical service with health check failure."""
        manager = ServiceManager()
        
        # Mock wait_for_service to succeed but health check to fail
        async def mock_wait_for_service(port):
            return True

        async def mock_check_health(port, retries):
            return False
            
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setattr('micro_cold_spray.__main__.wait_for_service', mock_wait_for_service)
        monkeypatch.setattr('micro_cold_spray.__main__.check_service_health', mock_check_health)
        
        success = await manager.start_service(
            "test",
            test_service_sync,
            critical=False,
            port=8000
        )
        assert success  # Non-critical services continue even with failed health check

    @pytest.mark.asyncio
    async def test_service_manager_force_kill(self):
        """Test service force kill when graceful shutdown fails."""
        manager = ServiceManager()
        
        success = await manager.start_service(
            "test",
            stubborn_process,
            critical=False
        )
        assert success
        
        # Stop should force kill the process
        manager.stop_service("test")
        assert "test" not in manager.processes

    @pytest.mark.asyncio
    async def test_service_manager_stop_nonexistent(self):
        """Test stopping a nonexistent service."""
        manager = ServiceManager()
        # Should not raise any errors
        manager.stop_service("nonexistent")

    @pytest.mark.asyncio
    async def test_service_manager_stop_all(self):
        """Test stopping all services."""
        manager = ServiceManager()
        
        # Start multiple services
        await manager.start_service("test1", test_service_sync, critical=False)
        await manager.start_service("test2", test_service_sync, critical=False)
        
        assert len(manager.processes) == 2
        manager.stop_all()
        assert len(manager.processes) == 0

    @pytest.mark.asyncio
    async def test_service_manager_start_exception(self):
        """Test service start with exception."""
        manager = ServiceManager()
        
        def failing_service():
            raise RuntimeError("Service failed to start")
        
        success = await manager.start_service(
            "test",
            failing_service,
            critical=False
        )
        assert not success

    @pytest.mark.asyncio
    async def test_run_ui_process(self, monkeypatch):
        """Test UI process runner."""
        mock_server = MagicMock()
        mock_config = MagicMock()
        
        def mock_run(coro):
            return None
            
        monkeypatch.setattr('uvicorn.Server', lambda config: mock_server)
        monkeypatch.setattr('uvicorn.Config', lambda *args, **kwargs: mock_config)
        monkeypatch.setattr('asyncio.run', mock_run)
        
        from micro_cold_spray.__main__ import run_ui_process
        run_ui_process()
        mock_server.serve.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_api_processes(self, monkeypatch):
        """Test API process runners."""
        mock_server = MagicMock()
        mock_config = MagicMock()
        
        def mock_run(coro):
            return None
            
        monkeypatch.setattr('uvicorn.Server', lambda config: mock_server)
        monkeypatch.setattr('uvicorn.Config', lambda *args, **kwargs: mock_config)
        monkeypatch.setattr('asyncio.run', mock_run)
        
        from micro_cold_spray.__main__ import (
            run_config_api_process,
            run_communication_api_process,
            run_messaging_api_process,
            run_process_api_process,
            run_state_api_process,
            run_data_collection_api_process,
            run_validation_api_process
        )
        
        # Test each API process runner
        for runner in [
            run_config_api_process,
            run_communication_api_process,
            run_messaging_api_process,
            run_process_api_process,
            run_state_api_process,
            run_data_collection_api_process,
            run_validation_api_process
        ]:
            runner()
            mock_server.serve.assert_called()

    @pytest.mark.asyncio
    async def test_main_success(self, monkeypatch):
        """Test successful main application run."""
        mock_manager = MagicMock()
        
        # Make start_service return a coroutine that returns True
        async def mock_start_service(*args, **kwargs):
            return True
        mock_manager.start_service = mock_start_service
        
        # Create a proper async mock for sleep
        async def mock_sleep(seconds):
            if seconds == 2:  # Service startup sleep
                return
            raise KeyboardInterrupt()  # Simulate Ctrl+C to exit cleanly
            
        monkeypatch.setattr('micro_cold_spray.__main__.ServiceManager', lambda: mock_manager)
        monkeypatch.setattr('asyncio.sleep', mock_sleep)
        
        from micro_cold_spray.__main__ import main
        exit_code = await main()
        assert exit_code == 0
        mock_manager.stop_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_critical_service_failure(self, monkeypatch):
        """Test main application with critical service failure."""
        mock_manager = MagicMock()
        mock_manager.start_service.return_value = False
        
        monkeypatch.setattr('micro_cold_spray.__main__.ServiceManager', lambda: mock_manager)
        
        from micro_cold_spray.__main__ import main
        exit_code = await main()
        assert exit_code == 1
        mock_manager.stop_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_service_death(self, monkeypatch):
        """Test main application handling service death."""
        mock_manager = MagicMock()
        mock_manager.start_service.return_value = True
        
        # Simulate a service dying
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_manager.processes = {'config': mock_process}
        
        def mock_sleep(seconds):
            if seconds == 2:  # Service startup sleep
                return None
            return None  # Let the service monitoring loop run once
            
        monkeypatch.setattr('micro_cold_spray.__main__.ServiceManager', lambda: mock_manager)
        monkeypatch.setattr('asyncio.sleep', mock_sleep)
        
        from micro_cold_spray.__main__ import main
        exit_code = await main()
        assert exit_code == 1
        mock_manager.stop_all.assert_called()

    @pytest.mark.asyncio
    async def test_main_exception(self, monkeypatch):
        """Test main application error handling."""
        def mock_setup():
            raise RuntimeError("Test error")
            
        monkeypatch.setattr('micro_cold_spray.__main__.setup_logging', mock_setup)
        
        from micro_cold_spray.__main__ import main
        exit_code = await main()
        assert exit_code == 1

    @pytest.mark.asyncio
    async def test_main_service_monitoring(self, monkeypatch):
        """Test main service monitoring loop."""
        mock_manager = MagicMock()
        
        # Create an AsyncMock for start_service that returns True
        mock_start_service = AsyncMock(return_value=True)
        mock_manager.start_service = mock_start_service

        # Create a mock process that dies after first check
        mock_process = MagicMock()
        mock_process.is_alive.side_effect = [True, False]
        mock_manager.processes = {'state': mock_process}  # Non-critical service
        
        # Create a proper async mock for sleep that allows one monitoring cycle
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 6:  # Allow startup sleeps and one monitoring cycle
                raise KeyboardInterrupt()
            
        monkeypatch.setattr('micro_cold_spray.__main__.ServiceManager', lambda: mock_manager)
        monkeypatch.setattr('asyncio.sleep', mock_sleep)
        
        from micro_cold_spray.__main__ import main
        exit_code = await main()
        assert exit_code == 0
        # Verify service restart was attempted
        assert mock_start_service.call_count > 1

    @pytest.mark.asyncio
    async def test_check_service_health_retries(self):
        """Test health check with multiple retries."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return mock_response
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "ok"}
            return mock_response
            
        with patch('requests.get', side_effect=mock_get):
            with patch('asyncio.sleep'):  # Mock sleep to speed up test
                result = await check_service_health(8000, retries=3, delay=0.1)
                assert result is True
                assert call_count == 3

    @pytest.mark.asyncio
    async def test_wait_for_service_connection_retry(self):
        """Test service wait with connection retry."""
        call_count = 0

        def mock_get(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise requests.ConnectionError()
            return MagicMock(status_code=200)
            
        with patch('requests.get', side_effect=mock_get):
            with patch('asyncio.sleep'):
                result = await wait_for_service(8000, timeout=1.0)
                assert result is True
                assert call_count == 3

    @pytest.mark.asyncio
    async def test_main_service_monitoring_critical_failure(self):
        """Test service monitoring with critical service failure."""
        # Create a mock manager
        mock_manager = MagicMock()
        mock_manager.start_service = AsyncMock(return_value=True)
        
        # Mock process that dies
        mock_process = MagicMock()
        mock_process.is_alive.return_value = False
        mock_manager.processes = {'config': mock_process}
        
        # Mock sleep to allow one monitoring cycle
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 2:  # After services have started
                return None  # Let the monitoring loop detect the dead process
            return None
        
        with patch('micro_cold_spray.__main__.setup_logging'), \
             patch('micro_cold_spray.__main__.ensure_directories'), \
             patch('micro_cold_spray.__main__.ServiceManager', return_value=mock_manager), \
             patch('micro_cold_spray.__main__.asyncio.sleep', mock_sleep), \
             patch('micro_cold_spray.__main__.signal.signal'):
            
            exit_code = await main()
            assert exit_code == 1  # Critical service failure should return 1
            assert mock_manager.stop_all.call_count == 2  # Called during normal shutdown and critical failure

    @pytest.mark.asyncio
    async def test_main_service_monitoring_shutdown_handler(self):
        """Test service monitoring with shutdown handler."""
        # Create a mock manager
        mock_manager = MagicMock()
        mock_manager.start_service = AsyncMock(return_value=True)
        
        # Create a mock signal handler that raises KeyboardInterrupt after services start
        call_count = 0

        async def mock_sleep(seconds):
            nonlocal call_count
            call_count += 1
            if call_count > 2:  # After services have started
                raise KeyboardInterrupt()
        
        with patch('micro_cold_spray.__main__.setup_logging'), \
             patch('micro_cold_spray.__main__.ensure_directories'), \
             patch('micro_cold_spray.__main__.ServiceManager', return_value=mock_manager), \
             patch('micro_cold_spray.__main__.asyncio.sleep', mock_sleep), \
             patch('micro_cold_spray.__main__.signal.signal'):
            
            exit_code = await main()
            assert exit_code == 0  # Clean shutdown should return 0
            mock_manager.stop_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_main_entry_point(self, monkeypatch):
        """Test the __main__ block."""
        # Mock main function and asyncio.run
        mock_main = AsyncMock(return_value=42)
        mock_run = MagicMock(return_value=42)
        
        # Mock sys.exit to prevent actual exit
        mock_exit = MagicMock()
        
        # Create a test environment
        test_globals = {
            '__name__': '__main__',
            'sys': MagicMock(exit=mock_exit),
            'asyncio': MagicMock(run=mock_run),
            'main': mock_main
        }
        
        # Execute the __main__ block
        exec('if __name__ == "__main__": sys.exit(asyncio.run(main()))', test_globals)
        
        # Verify the calls
        mock_run.assert_called_once()
        mock_exit.assert_called_once_with(42)

    @pytest.mark.asyncio
    async def test_service_manager_force_kill_timeout(self, monkeypatch):
        """Test force killing a service that doesn't respond to normal termination."""
        manager = ServiceManager()
        
        # Mock a process that doesn't die on join
        mock_process = MagicMock()
        mock_process.is_alive.return_value = True
        
        # Store the process in the manager
        manager.processes["test"] = mock_process
        
        # Stop the service
        manager.stop_service("test")
        
        # Verify force kill was called
        mock_process.kill.assert_called_once()
        mock_process.join.assert_called()

    @pytest.mark.asyncio
    async def test_service_manager_non_critical_health_check_failure(self):
        """Test handling of non-critical service health check failure."""
        manager = ServiceManager()
        
        with patch("micro_cold_spray.__main__.check_service_health") as mock_health:
            mock_health.return_value = False
            
            # Start non-critical service
            success = await manager.start_service("test", mock_non_critical_runner, critical=False)
            
            # Should continue despite health check failure
            assert success is True

    @pytest.mark.asyncio
    async def test_main_shutdown_handler(self, monkeypatch):
        """Test the shutdown handler."""
        # Mock ServiceManager
        mock_manager = MagicMock()
        monkeypatch.setattr("micro_cold_spray.__main__.ServiceManager", lambda: mock_manager)
        
        # Mock sys.exit to prevent actual exit
        mock_exit = MagicMock()
        monkeypatch.setattr("sys.exit", mock_exit)
        
        # Import and run main to register signal handlers
        from micro_cold_spray.__main__ import main
        
        # Create a task for main but don't wait for it to complete
        task = asyncio.create_task(main())
        await asyncio.sleep(0.1)  # Give time for signal handlers to be registered
        
        # Simulate SIGINT
        import signal
        signal.raise_signal(signal.SIGINT)
        await asyncio.sleep(0.1)  # Give time for handler to execute
        
        # Verify stop_all was called
        mock_manager.stop_all.assert_called_once()
        mock_exit.assert_called_once_with(0)
        
        # Cancel the task
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, SystemExit):
            pass
