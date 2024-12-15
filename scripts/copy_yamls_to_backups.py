import shutil
from pathlib import Path

# Correct the path to the config directory
CONFIG_DIR = Path('config')
BACKUP_DIR = CONFIG_DIR / 'backups'

# Ensure backup directory exists
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Copy all YAML files from config directory to backups
for yaml_file in CONFIG_DIR.glob('*.yaml'):
    backup_file = BACKUP_DIR / yaml_file.name
    shutil.copy2(yaml_file, backup_file)
    print(f"Copied {yaml_file} to {backup_file}")
