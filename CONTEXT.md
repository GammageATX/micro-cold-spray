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

### Infrastructure Layer

- **MessageBroker**: Central message routing system
  - Location: `src/micro_cold_spray/core/infrastructure/messaging/message_broker.py`
  - Single source of truth for pub/sub messaging
  - Handles all inter-component communication

- **ConfigManager**: Central configuration handler
  - Location: `src/micro_cold_spray/core/config/config_manager.py`
  - Single source of truth for all configurations
  - Handles runtime configuration updates

- **TagManager**: Hardware communication layer
  - Location: `src/micro_cold_spray/core/infrastructure/tags/tag_manager.py`
  - Single source of truth for hardware interaction
  - Only component that uses hardware clients

- **StateManager**: System state controller
  - Location: `src/micro_cold_spray/core/infrastructure/state/state_manager.py`
  - Single source of truth for system state
  - Manages all state transitions

- **UIUpdateManager**: UI update controller
  - Location: `src/micro_cold_spray/core/ui/ui_update_manager.py`
  - Single source of truth for UI updates
  - Manages all widget registrations and updates

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

### Monitor Components

1. Hardware Monitor:

   - Purpose: Monitor hardware status
   - Reports connection status
   - Reports hardware errors
   - Uses MessageBroker for all communication
   - Topics: hardware/status/*, hardware/error
2. Process Monitor:

   - Purpose: Monitor process parameters
   - Reports process status
   - Reports process errors
   - Uses MessageBroker for all communication
   - Topics: process/status/*, process/error
3. State Monitor:

   - Purpose: Monitor state transitions
   - Reports state changes
   - Reports invalid transitions
   - Uses MessageBroker for all communication
   - Topics: state/change, state/error

4. Monitor Operations:

   - Must use "hardware/status/*" for hardware updates
   - Must use "process/status/*" for process updates
   - Must use "state/change" for state updates
   - Must include timestamps in all messages
   - Must include error context in error messages

## Testing Standards

### Test Organization

1. Infrastructure Tests (Run First):
   - MessageBroker
   - ConfigManager
   - TagManager
   - StateManager

2. Process Tests:
   - ProcessValidator
   - ParameterManager
   - PatternManager
   - ActionManager
   - SequenceManager

3. UI Tests (Run Last):
   - UIUpdateManager
   - Widget tests

### Test Requirements

- Must use pytest framework
- Must use pytest-asyncio for async tests
- Must use pytest-qt for UI tests
- Must maintain test coverage standards
- Must use class-based structure
- Must follow component dependency order
- Must import TestOrder from conftest.py
- Must mark classes with correct dependency

### Test File Structure

- Must include descriptive docstring header
- Must document test requirements
- Must document test patterns
- Must document message patterns
- Must include run instructions

### Test Fixtures

- Must initialize required message topics
- Must provide proper cleanup
- Must handle async operations
- Must mock hardware clients

## Error Handling

### Required Checks

- All MessageBroker operations
- All cleanup chains
- All widget references
- All manager references

### Async Requirements

- All cleanup methods
- All UI update handlers
- All message operations
- All hardware operations

### Error Logging

- All exceptions must be caught and logged
- All error messages must be descriptive
- All error handlers must include context

### State Management

#### System States

1. Core States:
   - INITIALIZING: Initial state on system startup
     - Requires conditions: hardware.connected, config.loaded
     - Can transition to: READY

   - READY: System is initialized and operational
     - Requires conditions: hardware.connected, hardware.enabled
     - Can transition to: RUNNING, SHUTDOWN

   - RUNNING: System is executing operations
     - Requires conditions: hardware.connected, hardware.enabled, sequence.active
     - Can transition to: READY, ERROR

   - ERROR: System has encountered an error
     - No specific conditions required
     - Can transition to: READY, SHUTDOWN

   - SHUTDOWN: System is shutting down
     - Requires conditions: hardware.safe
     - Can transition to: INITIALIZING

#### State Conditions

- hardware.connected: Hardware communication established
- config.loaded: Configuration files loaded successfully
- hardware.enabled: Hardware systems are enabled
- sequence.active: Operation sequence is running
- hardware.safe: Hardware is in safe state for shutdown

#### State Transition Rules

- All transitions must be explicitly defined in state.yaml
- Each state must specify its required conditions
- Each state must list valid next_states
- Invalid transitions must raise StateError
- All transitions must be logged
- All state changes must be published to "state/change"
