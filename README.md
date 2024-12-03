# Micro Cold Spray Control System

Python control system for micro cold spray deposition processes.

## Features

- Real-time hardware control and monitoring
- Automated deposition sequences with pattern support
- Comprehensive process parameter management
- Multi-axis motion control
- Process validation and safety checks
- Data logging and analysis
- Mock hardware mode for development

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
    # Normal mode (requires hardware)
    python -m micro_cold_spray

    # Development mode (mock hardware)
    python -m micro_cold_spray --mock
    ```

## Development

### Project Structure

```text
micro-cold-spray/
├── config/                 # Configuration files
│   ├── application.yaml   # Core settings
│   ├── hardware.yaml      # Hardware config
│   ├── process.yaml       # Process parameters
│   ├── state.yaml        # State machine
│   └── tags.yaml         # PLC tag mapping
├── data/                  # Process data
│   ├── parameters/       # Process parameters
│   ├── patterns/         # Spray patterns
│   ├── sequences/        # Operation sequences
│   └── runs/            # Run history
├── src/                  # Source code
│   └── micro_cold_spray/
│       └── core/
│           ├── infrastructure/  # Core systems
│           ├── hardware/        # Hardware control
│           └── components/      # Main components
├── tests/                # Test suite
└── logs/                # Application logs
```

### Core Components

- **Infrastructure**: Message broker, config manager, state manager, tag manager
- **Hardware**: PLC and SSH communication, motion and equipment controllers
- **Process**: Validation system, data management
- **Operations**: Sequence management, pattern control, action handling
- **UI**: Dashboard, motion control, sequence editor, configuration

### Tools and Commands

```bash
# Testing
pytest                    # Run all tests
pytest tests/unit        # Run unit tests
pytest tests/integration # Run integration tests

# Code Quality
black .                  # Format code
pylint src/             # Lint code
mypy src/               # Type checking

# Development
python -m micro_cold_spray --mock  # Run with mock hardware
python -m micro_cold_spray --debug # Run with debug logging
```

### Dependencies

- PySide6>=6.4.0: Modern Qt-based GUI framework
- PyYAML>=6.0.1: Configuration file handling
- paramiko>=3.4.0: SSH communication
- productivity>=0.11.1: PLC communication
- pytest>=7.3.1: Testing framework
- loguru>=0.7.0: Advanced logging

## Contributing

1. Fork repository
2. Create feature branch
3. Follow code style guidelines in .cursorrules
4. Add tests for new features
5. Submit pull request

## License

MIT License

## Author

Michael Gammage (@GammageATX)
