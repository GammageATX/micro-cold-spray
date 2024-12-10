# 5. Data Collection API Design

Date: 2024-03-12

## Status

Accepted

## Context

The system needs to collect and store data during spray operations, including:
- Run-level metadata and configuration
- Individual spray event data
- Process parameters and status

We need a flexible solution that can:
1. Handle different storage backends
2. Maintain data integrity
3. Support real-time data collection
4. Integrate with sequence execution

## Decision

We will create a dedicated Data Collection API with:

1. Core Components:
   - `DataCollectionService`: Manages collection sessions and coordinates data storage
   - `SprayEvent`: Represents individual spray operations
   - `SprayDataStorage`: Abstract interface for storage implementations

2. Storage Strategy:
   - Run files (YAML) for sequence metadata and configuration
   - Separate storage for spray events (CSV initially, with TimescaleDB support planned)
   - Storage backend configurable through application config

3. Data Organization:
   ```
   data/
   ├── runs/
   │   ├── {sequence_id}_{timestamp}.yaml  # Run metadata
   │   └── spray_history.csv               # Spray event data
   └── sequences/
       └── {sequence_id}.yaml              # Sequence definitions
   ```

4. Integration Points:
   - Process API uses Data Collection service for sequence execution
   - MessageBroker for state notifications
   - ConfigManager for storage configuration

## Consequences

### Positive

1. Clear separation of concerns:
   - Data collection logic isolated from process control
   - Storage implementations independent of collection logic
   - Run data separate from spray event data

2. Flexibility:
   - Easy to add new storage backends
   - Storage configurable without code changes
   - Support for different data formats

3. Data Integrity:
   - Consistent data structure
   - Proper error handling
   - Event-based updates

### Negative

1. Additional Complexity:
   - More components to maintain
   - Need to manage multiple storage formats
   - Potential synchronization challenges

2. Performance Considerations:
   - CSV storage may not scale well
   - File I/O overhead
   - Need for future optimization

## Implementation Notes

1. Storage Interface:
   ```python
   class SprayDataStorage(ABC):
       async def save_spray_event(self, event: SprayEvent) -> None: ...
       async def update_spray_event(self, event: SprayEvent) -> None: ...
       async def get_spray_events(self, sequence_id: str) -> List[SprayEvent]: ...
   ```

2. Configuration:
   ```yaml
   data_collection:
     storage:
       type: csv  # or timescaledb
       dsn: "postgresql://..."  # for timescaledb
   ```

3. Event Flow:
   ```
   Process API -> Data Collection API -> Storage Backend
                                    -> MessageBroker (notifications)
   ```

## Future Work

1. Implement TimescaleDB storage for better performance
2. Add data retention policies
3. Implement data analysis endpoints
4. Add real-time data streaming capabilities
5. Enhance error recovery mechanisms 