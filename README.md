# Micro Cold Spray Control System

Python control system for micro cold spray deposition processes.

## Features
- Real-time hardware control
- Automated deposition sequences
- Process parameter management
- Equipment state monitoring
- Process validation

## Quick Start

1. Setup:

```bash
git clone https://github.com/GammageATX/micro-cold-spray.git
cd micro-cold-spray
python -m venv .venv
source .venv/Scripts/activate  # Windows
source .venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
pip install -e .
```

2. Run:

```bash
python -m micro_cold_spray
```

## Development

### Structure
```
micro-cold-spray/
├── config/     # Configuration files
├── data/       # Process data
├── src/        # Source code
├── tests/      # Test suite
└── logs/       # Application logs
```

### Tools
- Testing: `pytest`
- Format: `black .`
- Lint: `pylint src/`
- Types: `mypy src/`

### Dependencies
- PySide6: GUI framework
- PyYAML: Configuration
- paramiko: SSH communication
- productivity: PLC communication
- loguru: Logging

## Contributing
1. Fork repository
2. Create feature branch
3. Submit pull request

## License
[Add License]

## Author
Michael Gammage (@GammageATX)