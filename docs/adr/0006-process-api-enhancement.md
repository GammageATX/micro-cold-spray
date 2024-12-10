# Process API Enhancement

## Status
Proposed

## Context
While we've successfully moved several core functionalities into dedicated APIs (State, Communication, Data Collection), the Process API needs enhancement to fully encapsulate process control logic. Current challenges:

1. Process Management Needs:
   - Sequence execution control
   - Process parameter validation
   - Equipment state coordination
   - Real-time monitoring
   - Safety checks
   - Error recovery

2. Integration Requirements:
   - State API for system state
   - Communication API for hardware control
   - Data Collection API for logging
   - Pattern Generation for motion control

## Decision
We will enhance the Process API to be a fully encapsulated service handling all process control logic.

### Core Components

1. ProcessService:
   ```python
   class ProcessService(BaseService):
       def __init__(
           self,
           state_client: StateClient,
           comm_client: CommunicationClient,
           data_client: DataCollectionClient,
           pattern_manager: PatternManager,
           config_manager: ConfigManager,
           message_broker: MessageBroker
       ):
           self._state_client = state_client
           self._comm_client = comm_client
           self._data_client = data_client
           self._pattern_manager = pattern_manager
           self._config = config_manager
           self._broker = message_broker
           
           self._active_sequence = None
           self._process_state = ProcessState.IDLE
           self._safety_monitor = SafetyMonitor()
           self._parameter_validator = ParameterValidator()
   ```

2. Process Control Flow:
   ```python
   async def execute_sequence(self, sequence_id: str) -> None:
       try:
           # Validate sequence
           sequence = await self._load_and_validate_sequence(sequence_id)
           
           # Pre-execution checks
           await self._safety_monitor.check_conditions()
           await self._validate_equipment_state()
           
           # Initialize data collection
           await self._data_client.start_collection(sequence_id)
           
           # Execute sequence steps
           for step in sequence.steps:
               await self._execute_step(step)
               await self._verify_step_completion(step)
               
           # Cleanup
           await self._complete_sequence()
           
       except ProcessError as e:
           await self._handle_process_error(e)
   ```

3. Safety Management:
   ```python
   class SafetyMonitor:
       async def check_conditions(self) -> None:
           await self._verify_equipment_safety()
           await self._check_process_parameters()
           await self._verify_environmental_conditions()
           await self._check_motion_constraints()
   ```

4. REST Endpoints:
   ```
   POST   /api/process/sequences/{id}/start
   POST   /api/process/sequences/{id}/stop
   POST   /api/process/sequences/{id}/pause
   GET    /api/process/sequences/{id}/status
   POST   /api/process/parameters/validate
   GET    /api/process/safety/status
   POST   /api/process/patterns/generate
   POST   /api/process/patterns/validate
   GET    /api/process/patterns/{id}
   PUT    /api/process/patterns/{id}
   DELETE /api/process/patterns/{id}
   ```

### Integration Points

1. State Management:
   ```python
   async def _update_process_state(self, new_state: ProcessState) -> None:
       await self._state_client.transition_to(new_state.value)
       await self._broker.publish(
           "process.state_changed",
           {"state": new_state.value}
       )
   ```

2. Hardware Control:
   ```python
   async def _control_equipment(self, command: EquipmentCommand) -> None:
       try:
           await self._comm_client.send_command(command)
           await self._verify_command_execution(command)
       except CommunicationError as e:
           raise ProcessError("Equipment control failed") from e
   ```

3. Data Collection:
   ```python
   async def _log_process_data(self, data: ProcessData) -> None:
       await self._data_client.save_process_data(
           sequence_id=self._active_sequence.id,
           data=data
       )
   ```

4. Pattern Integration:
   ```python
   async def _execute_pattern(self, pattern_id: str) -> None:
       # Load pattern
       pattern = await self._pattern_manager.get_pattern(pattern_id)
       
       # Validate against current constraints
       constraints = await self._get_current_constraints()
       await self._pattern_manager.validate_pattern(pattern, constraints)
       
       # Execute motion
       for point in pattern.points:
           await self._move_to_point(point)
           await self._verify_position(point)
           await self._log_process_data(
               ProcessData(
                   type="motion",
                   data={"position": point}
               )
           )
   ```

## Consequences

### Positive
1. Clear process control boundaries
2. Centralized safety management
3. Consistent error handling
4. Better sequence control
5. Improved monitoring capabilities
6. Clean API interfaces

### Negative
1. More complex integration testing
2. Need to handle distributed system challenges
3. Must maintain API compatibility
4. Increased deployment complexity

## Implementation Plan

1. Phase 1 - Core Structure:
   - Basic service implementation
   - Safety monitoring
   - Parameter validation
   - Client integrations
   - Pattern generation integration

2. Phase 2 - Process Control:
   - Sequence execution
   - State management
   - Equipment control
   - Error handling
   - Pattern execution
   - Motion control

3. Phase 3 - Monitoring:
   - Real-time status
   - Data collection
   - Performance metrics
   - Health checks
   - Pattern execution monitoring
   - Position tracking

4. Phase 4 - Advanced Features:
   - Recovery procedures
   - Process optimization
   - Advanced validation
   - Diagnostic tools
   - Pattern optimization
   - Path planning improvements
   - Dynamic pattern adjustment

## References
- State API ADR
- Communication API ADR
- Data Collection API ADR
- Pattern Generation ADR (Now integrated into Process API)
- Core Architecture Rules 