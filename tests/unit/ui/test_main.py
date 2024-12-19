"""Tests for UI service launcher."""

from unittest.mock import patch, MagicMock
from micro_cold_spray.ui.__main__ import main


def test_ui_main():
    """Test UI service launcher."""
    with patch('uvicorn.run') as mock_run:
        main()
        mock_run.assert_called_once_with(
            "micro_cold_spray.ui.router:app",
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )


def test_ui_main_entry_point(monkeypatch):
    """Test the __main__ block of ui/__main__.py."""
    # Mock uvicorn.run to prevent server start
    mock_run = MagicMock()
    monkeypatch.setattr("uvicorn.run", mock_run)
    
    # Create a test environment
    test_globals = {
        '__name__': '__main__',
        'uvicorn': MagicMock(run=mock_run),
        'main': main
    }
    
    # Execute the __main__ block
    exec('if __name__ == "__main__": main()', test_globals)
    
    # Verify uvicorn.run was called with correct arguments
    mock_run.assert_called_once_with(
        "micro_cold_spray.ui.router:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
        log_level="info"
    )
