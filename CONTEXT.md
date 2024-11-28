# Project Context

## System Overview
The Micro Cold Spray system is an automated manufacturing solution that controls hardware equipment for material deposition processes.

## Development Environment

### Python Environment
1. Virtual Environment Setup:
   ```bash
   python -m venv .venv
   source .venv/Scripts/activate  # Windows with Git Bash
   # OR
   .venv\Scripts\activate        # Windows CMD
   # OR
   source .venv/bin/activate     # Linux/Mac
   ```

2. Package Installation:
   ```bash
   pip install -r requirements.txt
   pip install -e .  # Install package in development mode
   ```

3. Running the Application:
   ```bash
   python -m micro_cold_spray
   # OR
   python src/micro_cold_spray/__main__.py
   ```

## Core Components

### State Management
- **StateManager**: Maintains the system's state machine
- **Location**: `src/micro_cold_spray/core/infrastructure/state/state_manager.py`
- **Configuration**: `config/state.yaml`
- **Monitor**: `src/micro_cold_spray/core/infrastructure/state/state_monitor.py`
- **HardwareMonitor**: `src/micro_cold_spray/core/infrastructure/state/hardware_monitor.py`
- **ProcessMonitor**: `src/micro_cold_spray/core/infrastructure/state/process_monitor.py`

### Configuration System
- **ConfigManager**: Central configuration handler
- **Location**: `src/micro_cold_spray/core/config/config_manager.py`
- **Configuration Files**:
  - `config/application.yaml`: Application-wide settings
  - `config/hardware.yaml`: Hardware configuration
  - `config/messaging.yaml`: Message broker configuration
  - `config/operations.yaml`: Operation-specific parameters
  - `config/process.yaml`: Process-specific parameters
  - `config/state.yaml`: State machine definitions
  - `config/tags.yaml`: Tag definitions
  - `config/ui.yaml`: UI configuration

### Hardware Control
- **EquipmentController**: Manages hardware equipment
- **MotionController**: Handles motion control systems
- **Locations**:
  - `src/micro_cold_spray/core/hardware/controllers/equipment_controller.py`
  - `src/micro_cold_spray/core/hardware/controllers/motion_controller.py`

### Process Management
- **ProcessValidator**: Validates process parameters and configurations
- **ParameterManager**: Handles operation parameters
- **SequenceManager**: Controls operation sequences
- **PatternManager**: Manages deposition patterns
- **ActionManager**: Manages actions both atomic and compound
- **Locations**:
  - `src/micro_cold_spray/core/components/process/validation/process_validator.py`
  - `src/micro_cold_spray/core/components/operations/parameters/parameter_manager.py`
  - `src/micro_cold_spray/core/components/operations/sequences/sequence_manager.py`
  - `src/micro_cold_spray/core/components/operations/patterns/pattern_manager.py`
  - `src/micro_cold_spray/core/components/process/actions/action_manager.py`

### Tag Management
- **TagManager**: Central registry for all system tags
- **Location**: `src/micro_cold_spray/core/infrastructure/tags/tag_manager.py`

### Hardware Tag Management

1. PLC Tags:
   - Use exact tag names from CSV file
   - Regular polling required
   - Async communication pattern
   - Examples:
     - XAxis.Target, YAxis.Target, ZAxis.Target
     - XAxis.Velocity, XAxis.Accel, XAxis.Decel
     - MoveX, MoveY, MoveZ (triggers)
     - XAxis.InProgress, YAxis.InProgress
     - XYMove.LINVelocity, XYMove.XPosition
     - MainSwitch, FeederSwitch, VentSwitch
     - MainFlowRate, FeederFlowRate
     - ChamberPressure

2. SSH Tags (Powder Feeder):
   - Simple command interface via paramiko
   - No polling required
   - Commands:
     - P-value settings
     - Power on/off
   - State tracked internally

## Core Manager Access Patterns

1. ConfigManager
   - Purpose: Provides static configuration access
   - Direct Access: Allowed for all components
   - Usage: Constructor injection for initial setup
   - Runtime Updates: Received via MessageBroker

2. TagManager
   - Purpose: Hardware communication management
   - Direct Access: None - all components use MessageBroker
   - Only component that uses hardware clients
   - Manages all tag reads/writes through clients
   - Publishes updates via MessageBroker

3. MessageBroker
   - Purpose: System-wide communication
   - Used by all components for:
     - Hardware commands (through TagManager)
     - State changes
     - Configuration updates
     - Status monitoring
     - Error reporting

## Project Organization

### Code Organization
- Core functionality in `src/micro_cold_spray/core/`
- Configuration files in `config/`
- Run data stored in `data/runs`
- Parameter files stored in `data/parameters`
- Pattern files stored in `data/patterns`
- Sequence files stored in `data/sequences`
- Tests in `tests/`
- Program log in `logs/`

### Testing Requirements
- All new features require corresponding tests
- Test files must include command and description headers
- Integration tests should verify component interactions

### Documentation Standards
- Keep README.md updated with setup and usage instructions
- Maintain TODO.md for tracking development tasks
- Document architectural decisions in commit messages

### Version Control
- Follow .gitignore for excluding files
- Respect .cursorignore patterns
- Commit messages should reference relevant issues/tasks 

### Message Patterns

1. Tag Access:
   - Write: Components send "tag/set" with {tag, value}
   - Read: Components send "tag/get" with {tag}
   - Updates: Components receive "tag_update" with {tag: value}
   - Responses: Components receive "tag_get_response" with {tag, value}

2. Command/Response:
   - Components can use MessageBroker.request() for synchronous operations
   - Used for status monitoring and value retrieval
   - Includes timeout handling
   - Returns response or raises exception

3. State Operations:
   - Must use "state/request" for requesting state changes
   - Must use "state/change" for observing state updates
   - Must use "state/error" for state operation errors
   - Must get state directly from StateManager
   - Must not store state in tags

## Dependencies

### Core Dependencies
- PySide6: Qt6 GUI framework
- PyYAML: YAML configuration handling
- paramiko: SSH communication
- productivity: PLC communication
- loguru: Enhanced logging

### Development Tools
- pytest: Testing framework
- pytest-asyncio: Async testing support
- pytest-qt: Qt testing support
- mypy: Type checking
- black: Code formatting
- pylint: Code linting
- pytest-cov: Test coverage
- pytest-mock: Mocking support

## Access Patterns

1. Direct Access Components:
   - ConfigManager:
     - Direct access allowed for all components
     - Used for static configuration loading
     - Runtime updates received via MessageBroker
   - StateManager:
     - Direct access for state queries
     - State changes via set_state()
     - State updates observed via state/change

2. MessageBroker Communication:
   - Required for all runtime communication
   - Required for all hardware commands
   - Required for all configuration updates
   - Required for all error reporting
   - Used for observing state changes
   - Handles command/response patterns

3. State Management:
   - StateManager is single source of truth
   - Components get state directly from StateManager
   - Components observe state changes via state/change
   - Invalid transitions publish to error topic
   - State not stored in tags

4. Hardware Communication:
   - TagManager:
     - Only component to use hardware clients
     - Manages all hardware read/write operations
     - Publishes hardware updates via MessageBroker
     - Uses exact PLC tag names from hardware

5. UI Updates:
   - UIUpdateManager:
     - Manages all UI component updates
     - Handles widget registration
     - Routes updates to widgets
     - Forwards config updates to UI