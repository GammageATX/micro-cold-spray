# State API Integration

## Status
Accepted

## Context
We are moving state management functionality from the core project into a dedicated API. This is part of our broader strategy to encapsulate core functionality into self-contained APIs. Key considerations:

1. Current State:
   - State management logic in core `StateManager`
   - State definitions in `state.yaml`
   - Tight coupling with core components
   - Mixed responsibilities

2. Goals:
   - Full encapsulation of state management in API
   - Clear separation from core project
   - Self-contained state logic
   - Independent deployment capability
   - Clean interfaces for other services

## Decision
We will move all state management functionality into the State API, making it a fully encapsulated service. The API will:

1. Take Full Ownership:
   - Move state management logic from core
   - Own state definitions and validation
   - Handle all state persistence
   - Manage state transitions
   - Control state history

2. Provide Clean Interfaces:
   - REST API for external access
   - Message broker for event notifications
   - Configuration management
   - State validation rules
   - Condition checking

3. REST Endpoints:
   - GET `/api/state/current` - Current state
   - POST `/api/state/transition/{target_state}` - State transitions
   - GET `/api/state/history` - State history
   - GET `/api/state/valid-transitions` - Valid state transitions
   - GET `/api/state/conditions` - State conditions

4. Handle All Concerns:
   - State persistence
   - Error handling
   - Event notifications
   - System monitoring
   - Safety checks
   - Configuration management

## Consequences

### Positive
1. Clear separation of concerns
2. Self-contained state management
3. Independent deployment and scaling
4. Easier testing and maintenance
5. Clean interfaces for other services
6. Reduced core project complexity

### Negative
1. Need to carefully migrate existing functionality
2. Must maintain backward compatibility during transition
3. More complex API implementation
4. Need to handle all dependencies internally

## Implementation Notes

1. Service Structure:
   ```python
   class StateService(BaseService):
       def __init__(
           self,
           config_manager: ConfigManager,
           message_broker: MessageBroker
       ):
           super().__init__(service_name="state")
           self._config_manager = config_manager
           self._message_broker = message_broker
           self._current_state = "INITIALIZING"
           self._state_history = []
           self._state_conditions = {}
           
           # Load state definitions
           self._load_state_config()
           self._setup_event_handlers()
   ```

2. State Management:
   ```python
   async def transition_to(self, target_state: str) -> None:
       # Internal validation
       await self._validate_transition(target_state)
       
       # Pre-transition tasks
       await self._notify_transition_start(target_state)
       
       # Update state
       old_state = self._current_state
       self._current_state = target_state
       
       # Record history
       self._record_transition(old_state, target_state)
       
       # Post-transition tasks
       await self._handle_post_transition(target_state)
   ```

3. Configuration:
   ```yaml
   # state.yaml in API
   state:
     transitions:
       READY:
         conditions:
           - hardware.connected
           - hardware.enabled
         next_states:
           - RUNNING
           - SHUTDOWN
           - IDLE
           - ERROR
   ```

## Migration Plan
1. Create new state management in API
2. Add new endpoints and functionality
3. Gradually move core functionality to API
4. Update clients to use API
5. Remove old core implementation

## References
- Core architecture rules
- Original `state.yaml`
- Current `StateManager` implementation
- Communication API ADR 