# Micro Cold Spray Control System

A Python-based control system for micro cold spray deposition processes. This system provides automated control and monitoring of cold spray equipment for precision material deposition.

## Features

- Real-time hardware control and monitoring
- Automated deposition sequence management
- Pattern-based deposition control
- Process parameter management
- Equipment state monitoring
- Configurable process validation

## Installation

1. Clone the repository:
```bash
git clone https://github.com/GammageATX/micro-cold-spray.git
cd micro-cold-spray
```

2. Create and activate virtual environment:
```bash
python -m venv .venv

# Windows (Git Bash)
source .venv/Scripts/activate

# Windows (CMD)
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
pip install -e .
```

## Running the Application

```bash
python -m micro_cold_spray
```

## Development

### Project Structure
```
micro-cold-spray/
├── config/               # Configuration files
├── data/                # Data storage
│   ├── parameters/      # Process parameters
│   ├── patterns/        # Deposition patterns
│   ├── runs/           # Run data
│   └── sequences/      # Operation sequences
├── src/                 # Source code
│   └── micro_cold_spray/
│       └── core/       # Core functionality
├── tests/              # Test suite
└── logs/               # Application logs
```

### Testing
```bash
pytest
```

### Code Quality
- Format code with black: `black .`
- Run linting: `pylint src/`
- Type checking: `mypy src/`

## Dependencies

### Core Dependencies
- PySide6: Qt6 GUI framework
- PyYAML: Configuration handling
- paramiko: SSH communication
- productivity: PLC communication
- loguru: Enhanced logging

### Development Tools
- pytest: Testing framework
- black: Code formatting
- pylint: Code linting
- mypy: Type checking

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add License Information]

## Authors

- Michael Gammage (@GammageATX) 