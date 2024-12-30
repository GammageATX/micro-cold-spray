"""Process API main script."""

import os
import yaml
import uvicorn
from pathlib import Path
from typing import Dict, Any
from loguru import logger


def load_config() -> Dict[str, Any]:
    """Load configuration from file.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file not found
    """
    config_path = Path("config/process.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path) as f:
        return yaml.safe_load(f)


def main() -> None:
    """Main function for running Process API service."""
    try:
        # Verify config exists and is valid
        config = load_config()
        logger.info(f"Loaded process configuration version {config.get('version', '1.0.0')}")
        
        # Configure uvicorn
        uvicorn.run(
            "micro_cold_spray.api.process.process_app:create_process_service",
            host="0.0.0.0",
            port=8004,
            factory=True,
            reload=True,
            log_level="info",
            lifespan="on",
            timeout_keep_alive=60
        )
        
    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"Failed to start Process API service: {e}")
        raise


if __name__ == "__main__":
    main()
