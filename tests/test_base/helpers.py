"""Test helper functions."""

from pathlib import Path
import yaml
import shutil


def get_config_dir() -> Path:
    """Get the real config directory."""
    return Path("micro_cold_spray/api/config")


def setup_test_config(tmp_path: Path) -> Path:
    """Set up a test config directory using real config files."""
    test_config_dir = tmp_path / "config"
    test_config_dir.mkdir(exist_ok=True)
    
    # Copy real config files
    real_config_dir = get_config_dir()
    for config_file in real_config_dir.glob("*.yaml"):
        shutil.copy2(config_file, test_config_dir / config_file.name)
    
    return test_config_dir


def load_yaml_file(file_path: Path) -> dict:
    """Load YAML file."""
    with open(file_path) as f:
        return yaml.load(f, Loader=yaml.Loader)


def create_test_config(tmp_path: Path, name: str, data: dict) -> Path:
    """Create a test config file."""
    config_path = tmp_path / "config" / f"{name}.yaml"
    config_path.parent.mkdir(exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(data, f)
    return config_path
