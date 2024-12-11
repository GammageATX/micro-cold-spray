"""Config API for managing configuration files."""

import yaml
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Config API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config directory
CONFIG_DIR = Path("config")
CONFIG_DIR.mkdir(exist_ok=True)


@app.get("/health")
async def health_check():
    """Check if API is running and config dir is accessible."""
    try:
        # Check if config dir exists and is writable
        if not CONFIG_DIR.exists() or not os.access(CONFIG_DIR, os.W_OK):
            return {
                "status": "Error",
                "error": "Config directory not accessible"
            }
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }


@app.get("/configs")
async def list_configs():
    """List available config files."""
    try:
        configs = [f.stem for f in CONFIG_DIR.glob("*.yaml")]
        return {"configs": configs}
    except Exception as e:
        return {"error": str(e)}


@app.get("/configs/{name}")
async def get_config(name: str):
    """Get contents of a config file."""
    try:
        config_file = CONFIG_DIR / f"{name}.yaml"
        if not config_file.exists():
            return {"error": f"Config {name} not found"}
            
        with open(config_file) as f:
            return yaml.safe_load(f)
    except Exception as e:
        return {"error": str(e)}


@app.post("/configs/{name}")
async def save_config(name: str, config: dict):
    """Save a config file."""
    try:
        config_file = CONFIG_DIR / f"{name}.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config, f)
        return {"status": "saved"}
    except Exception as e:
        return {"error": str(e)}


@app.post("/configs/{name}/validate")
async def validate_config(name: str, config: dict):
    """Validate config without saving."""
    try:
        # Basic validation - check if it's valid YAML
        yaml.dump(config)
        return {"valid": True}
    except Exception as e:
        return {
            "valid": False,
            "error": str(e)
        }


@app.delete("/configs/{name}")
async def delete_config(name: str):
    """Delete a config file."""
    try:
        config_file = CONFIG_DIR / f"{name}.yaml"
        if not config_file.exists():
            return {"error": f"Config {name} not found"}
        config_file.unlink()
        return {"status": "deleted"}
    except Exception as e:
        return {"error": str(e)}
