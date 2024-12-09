# Micro Cold Spray Control System

## Architecture Overview

The Micro Cold Spray Control System uses a distributed architecture with clear component responsibilities:

### Core Components

#### UI Update Manager

Simple tag update distributor that:

- Registers widgets for tag updates
- Distributes tag updates from TagManager to interested widgets
- Handles widget cleanup

#### Tag Manager

Hardware interface that:

- Manages all hardware communication
- Maintains tag state
- Polls hardware for updates
- Distributes updates via UIUpdateManager

#### Message Broker

Messaging system that:

- Handles all pub/sub messaging
- Routes requests/responses
- Enables direct component communication

#### Config Manager

Configuration handler that:

- Manages all system configuration
- Validates configuration changes
- Persists configuration state

#### State Manager

State controller that:

- Manages system state transitions
- Validates state changes
- Maintains system state

#### Data Manager

Data handler that:

- Manages process data
- Handles data persistence
- Validates data operations

### UI Component Design

UI components follow these principles:

1. **Widget Base**
   - All widgets inherit from BaseWidget
   - Register with UIUpdateManager for tag updates
   - Handle own error states and recovery
   - Manage own widget state

2. **Communication**
   - Use MessageBroker for component communication
   - Use UIUpdateManager only for tag updates
   - Direct requests to appropriate managers (Config, Data, etc.)

3. **Error Handling**
   - Each component handles its own errors
   - Log errors with context
   - Implement recovery procedures
   - Maintain safety during errors

4. **State Management**
   - Components manage their own state
   - Use MessageBroker for state updates
   - Handle state transitions gracefully

## Development Guidelines

1. **Component Responsibilities**
   - Keep components focused on single responsibility
   - Avoid circular dependencies
   - Use proper manager for each operation type
   - Follow established communication patterns

2. **Error Handling**
   - Log all errors with context
   - Implement proper cleanup
   - Handle async operations correctly
   - Maintain system safety

3. **Testing**
   - Write unit tests for new features
   - Test error conditions
   - Verify async operations
   - Test state transitions

4. **Documentation**
   - Document public interfaces
   - Update architecture docs for changes
   - Include examples for new features
   - Document error handling
