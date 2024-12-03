# Project Context

## System Overview

The Micro Cold Spray system is an automated manufacturing solution that controls hardware equipment for material deposition processes. It provides comprehensive control over gas flows, powder feeding, motion systems, and process parameters while ensuring safety and process quality.

## Core Architecture

### Infrastructure Layer

1. **MessageBroker**:
   - Central message routing system
   - Asynchronous pub/sub patterns
   - Request/response handling
   - Error propagation
   - Event coordination

2. **ConfigManager**:
   - Configuration validation and loading
   - Runtime updates
   - Configuration persistence
   - Default value management
   - Change notification

3. **TagManager**:
   - Hardware communication
   - Tag state management
   - Mock hardware support
   - Connection management
   - Value validation

4. **StateManager**:
   - State machine implementation
   - Transition validation
   - State persistence
   - Error recovery
   - State history

5. **DataManager**:
   - Process data collection
   - Run history management
   - Data analysis
   - Backup handling
   - Data export

### Process Control

1. **Validation System**:
   - Parameter validation
   - Safety checks
   - Pattern validation
   - Sequence validation
   - Hardware validation

2. **Operation Control**:
   - Sequence execution
   - Pattern management
   - Action coordination
   - Error handling
   - Progress tracking

3. **Hardware Control**:
   - Motion systems
   - Gas control
   - Powder feeding
   - Vacuum system
   - Safety interlocks

### User Interface

1. **Main Components**:
   - Dashboard
   - Motion control
   - Sequence editor
   - Configuration
   - Diagnostics

2. **Widget System**:
   - Real-time updates
   - State visualization
   - Error display
   - Process control
   - Data visualization

## Development Guidelines

### Code Organization

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

### Development Workflow

1. **Setup Environment**:

   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows
   source .venv/bin/activate     # Linux/Mac
   pip install -r requirements.txt
   pip install -e .
   ```

2. **Development Commands**:

   ```bash
   # Testing
   pytest                    # Run all tests
   pytest tests/unit        # Unit tests
   pytest tests/integration # Integration tests
   
   # Code Quality
   black .                  # Format code
   pylint src/             # Lint code
   mypy src/               # Type checking
   
   # Development Mode
   python -m micro_cold_spray --mock  # Mock hardware
   python -m micro_cold_spray --debug # Debug logging
   ```

### Communication Patterns

1. **Hardware Communication**:
   - Tag writes: `tag/set` with `{tag, value}`
   - Tag reads: `tag/get` with `{tag}`
   - Updates: `tag_update` with `{tag: value}`
   - Responses: `tag_get_response` with `{tag, value}`

2. **State Management**:
   - State requests: `state/request`
   - State changes: `state/change`
   - State errors: `state/error`
   - Direct state queries via StateManager

3. **Process Control**:
   - Sequence control: `sequence/*`
   - Pattern execution: `pattern/*`
   - Action management: `action/*`
   - Validation: `validation/*`

### Safety Guidelines

1. **Hardware Safety**:
   - Always validate parameters
   - Check motion limits
   - Monitor pressures
   - Verify gas flows
   - Handle emergencies

2. **Process Safety**:
   - Validate sequences
   - Check patterns
   - Monitor powder feed
   - Track vacuum levels
   - Log all operations

3. **Error Handling**:
   - Graceful degradation
   - Safe state fallback
   - User notification
   - Error logging
   - Recovery procedures

## Dependencies

### Core Dependencies

- PySide6>=6.4.0: Modern Qt-based GUI framework
- PyYAML>=6.0.1: Configuration file handling
- paramiko>=3.4.0: SSH communication
- productivity>=0.11.1: PLC communication
- pytest>=7.3.1: Testing framework
- loguru>=0.7.0: Advanced logging

### Development Tools

- black: Code formatting
- pylint: Code linting
- mypy: Type checking
- pytest-qt: Qt testing
- pytest-asyncio: Async testing
- pytest-cov: Coverage reporting

## Version Control

### Commit Guidelines

- Use descriptive messages
- Reference issues
- Document changes
- Tag releases
- Update changelog

### Branch Strategy

- main: Stable releases
- develop: Integration
- feature/*: New features
- bugfix/*: Bug fixes
- release/*: Release prep
