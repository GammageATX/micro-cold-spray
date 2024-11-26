# Project Context

## System Overview
The Micro Cold Spray system is an automated manufacturing solution that controls hardware equipment for material deposition processes.

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
  - `config/ui.yaml`: UI configuration (not yet implemented)

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

3. Tag Access:
   - All components use "tag/set" and "tag/get"
   - No translation between PLC and internal names
   - Direct mapping to hardware tags
   - Clear hardware tag documentation
   - Consistent naming across system

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

4. Component Communication Flow:
   - UI/Component -> MessageBroker -> Controller
   - Controller -> MessageBroker -> TagManager
   - TagManager -> Client -> Hardware
   - Hardware -> Client -> TagManager -> MessageBroker -> Components

## Architecture Principles

### Single Source of Truth
1. **TagManager**
   - Purpose: Central registry for all system tags
   - Ensures consistent tag naming and usage
   - Is the only component that can read tags from the hardware
   - Also maintains all internal tags used by the software

2. **ConfigManager**
   - Purpose: Unified configuration management
   - Prevents duplicate or conflicting configurations
   - Manages all YAML configuration files

3. **MessageBroker**
   - Purpose: Centralized message handling
   - Manages all publish/subscribe operations
   - Ensures consistent message routing
   - Loads with a direct connection to its config file but then establishes a pub/sub relationship with the MessageBroker

4. **UIUpdateManager**
   - Purpose: Unified UI state management
   - Controls all UI updates
   - Maintains UI consistency

5. **DataManager**
   - Purpose: Data collection and storage
   - Manages all data collection and storage

### Data Flow
1. Configuration data flows from YAML files through ConfigManager
2. State changes are managed by StateManager and updated through the MessageBroker to the TagManager
3. Hardware operations are coordinated through controllers and updated through the MessageBroker to the TagManager
4. Process execution follows validated sequences

### Hardware Communication Flow

1. Command Path (Write):
   UI/Component -> MessageBroker -> Controller -> MessageBroker -> TagManager -> Client -> Hardware
   
   Example:
   ```
   UI sends: "motion/command/move" -> MotionController
   Controller validates and sends: "tag/set" with "motion.command.move" -> TagManager
   TagManager uses appropriate client to write to hardware
   ```

2. Status Path (Read):
   Hardware -> Client -> TagManager -> MessageBroker -> Components
   
   Example:
   ```
   Hardware updates position
   Client reads hardware
   TagManager polls client
   TagManager publishes updates via MessageBroker
   Components receive "motion/position" updates
   ```

3. Validation Layers:
   - Controllers: Basic hardware limit validation
   - ProcessValidator: Process-level validation
   - TagManager: Hardware interface validation
   - Hardware: Physical limits and interlocks

4. Status Monitoring:
   - Components request status via "tag/get"
   - TagManager maintains current values
   - Updates published via MessageBroker
   - Error conditions broadcast to all subscribers

## Development Guidelines

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

### Hardware Control Architecture

1. Equipment Control:
   - Gas System Management:
     ```
     UI -> equipment/gas/flow -> EquipmentController -> tag/set -> TagManager -> PLC
     UI -> equipment/gas/valve -> EquipmentController -> tag/set -> TagManager -> PLC
     ```

   - Vacuum System Management:
     ```
     UI -> equipment/vacuum/pump -> EquipmentController -> tag/set (momentary) -> TagManager -> PLC
     UI -> equipment/vacuum/valve -> EquipmentController -> tag/set -> TagManager -> PLC
     ```

   - Powder Feed System:
     ```
     UI -> equipment/feeder -> EquipmentController -> tag/set -> TagManager -> SSH
     UI -> equipment/deagglomerator -> EquipmentController -> tag/set -> TagManager -> PLC
     ```

2. Motion Control:
   ```
   UI -> motion/command/move -> MotionController -> tag/set -> TagManager -> PLC
   UI -> motion/command/home -> MotionController -> tag/set -> TagManager -> PLC
   ```

3. Hardware Clients:
   - PLC Client:
     - All critical hardware I/O
     - Regular status polling
     - Synchronous communication
   - SSH Client:
     - Powder feeder only
     - No status polling
     - Simple command interface

# Qt Style Constants

## Frame Styles
Use proper Qt6 enum classes for frame styles:
```python
# Correct:
frame.setFrameShape(QFrame.Shape.StyledPanel)
frame.setFrameShadow(QFrame.Shadow.Raised)

# Incorrect:
frame.setFrameShape(QFrame.StyledPanel)  # Qt5 style
frame.setFrameShadow(QFrame.Raised)      # Qt5 style
```

## Alignment Flags
Use proper Qt6 alignment flag enums:
```python
# Correct:
label.setAlignment(Qt.AlignmentFlag.AlignCenter)

# Incorrect:
label.setAlignment(Qt.AlignCenter)  # Qt5 style
```

## Size Policies
Use proper Qt6 size policy enums:
```python
# Correct:
widget.setSizePolicy(
    QSizePolicy.Policy.Expanding,
    QSizePolicy.Policy.Fixed
)

# Incorrect:
widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)  # Qt5 style
```

## ComboBox Policies
Use proper Qt6 combo box enums:
```python
# Correct:
combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)

# Incorrect:
combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)  # Qt5 style
```

# Message Patterns

## MessageBroker Communication

1. **Publish/Subscribe Pattern**
   ```python
   # Publishing
   await message_broker.publish("topic", data)
   
   # Subscribing
   message_broker.subscribe("topic", callback)
   ```

2. **Request/Response Pattern**
   ```python
   # Making a request
   response = await message_broker.request("topic", data, timeout=5.0)
   
   # Handling responses
   if response:
       value = response.get('value')
   ```

3. **Message Structure**
   - Request Messages:
     ```python
     {
         "request_id": "unique_id",
         "timestamp": "iso_timestamp",
         "tag": "tag_name",  # or other request-specific data
         ...
     }
     ```
   - Response Messages:
     ```python
     {
         "request_id": "matching_id",
         "value": response_data,
         "timestamp": "iso_timestamp",
         ...
     }
     ```

4. **Response Topics**
   - Format: "{original_topic}_response"
   - Example: "tag/get" -> "tag/get_response"
   - Automatically handled by MessageBroker

5. **Timeouts**
   - Default: 5.0 seconds
   - Configurable per request
   - Returns None on timeout
   - Cleanup handled automatically

# Dependency and Error Handling Patterns

## None Checks
1. Message Broker Operations:
```python
if self._message_broker is None:
    logger.error("Cannot perform operation - no message broker")
    return
```

2. Widget Cleanup Chain:
```python
if hasattr(self, '_widget') and self._widget is not None:
    if hasattr(self._widget, 'cleanup') and callable(self._widget.cleanup):
        await self._widget.cleanup()
```

3. Super Cleanup:
```python
await super(CurrentClass, self).cleanup()
```

## Configuration Access
1. Core Services:
- Direct access to ConfigManager allowed
- Must handle missing configs gracefully
- Must publish config changes through MessageBroker

2. UI Components:
- No direct ConfigManager access
- Must use UIUpdateManager for all config operations
- Must subscribe to config updates they care about

## Message Flow
1. Config Changes:
```
UI Widget -> UIUpdateManager -> MessageBroker -> ConfigManager
                                             -> Subscribers
```

2. Hardware Commands:
```
UI Widget -> UIUpdateManager -> MessageBroker -> TagManager -> Hardware
```

3. Status Updates:
```
Hardware -> TagManager -> MessageBroker -> UIUpdateManager -> UI Widgets
```