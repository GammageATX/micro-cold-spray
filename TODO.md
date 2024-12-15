# Topic Structure Update Tasks

## 1. Communication Service

- Update CommunicationService to handle new topic structure
- Move direct SSH/hardware calls into proper hardware topics
- Remove tag-based operations from external API
- Implement request/response handlers for each topic type

## 2. Hardware Service

- Create dedicated handlers for each hardware component:
  - Feeder control
  - Deagglomerator control
  - Gas control
  - Valve control
  - Vacuum control
  - Motion control
  - Nozzle control
- Move tag logic inside hardware service

## 3. File Operations

- Update parameter file handling
- Add nozzle file operations
- Add powder file operations
- Update pattern operations
- Update sequence operations with generate

## 4. Action System

- Update action_atomic handlers
- Update action_group handlers
- Move hardware-specific actions to hardware topics

## 5. State Management

- Update state change notifications
- Update state request/response handlers
- Move hardware state to hardware topics

## 6. UI Updates

- Update UI to use new topic structure
- Update state displays
- Update hardware control panels
- Update file operation dialogs

## 7. Configuration

- Update message broker configuration
- Update service configurations
- Update validation schemas

## 8. Testing

- Update test mocks for new topics
- Add tests for new operations
- Update integration tests
- Update hardware simulation

## Implementation Notes

- Keep hardware implementation details (tags, SSH, PLC) internal to communication service
- Use simple action-based API for external services
- Maintain consistent request/response pattern across all topics
- Ensure proper error handling and validation
