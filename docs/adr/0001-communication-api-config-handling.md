# Communication API Config Handling

## Status

Accepted

## Context

The Communication API needs to handle configuration changes for:

- PLC tag definitions
- Hardware connection settings
- Feeder P-variable mappings
- Polling intervals

We considered two approaches:

1 Live updates: Services handle config changes while running
2 Restart approach: Services restart when configs change

## Decision

We will use the restart approach where services fully shutdown and reinitialize when configs change.

### Key Components

1 **Base Service**

- Loads configs on initialization
- Subscribes to config updates
- Implements clean shutdown
- Restarts on config changes

2 **PLC Service**

- Manages PLC connection
- Handles tag polling
- Maintains tag cache
- Clean connection shutdown

3 **Feeder Service**

- Manages SSH connection
- Maps tag paths to P-variables
- Caches written values
- Clean connection shutdown

## Consequences

### Positive

- Simpler implementation
- Cleaner state management
- More reliable config updates
- Easier to debug
- No partial update states

### Negative

- Brief service interruption during restart
- All operations paused during restart
- Potential loss of cached values

## Implementation Notes

```python
# Base restart flow
async def handle_config_update(self):
    """Handle any config update by triggering service restart."""
    await self.shutdown()   # Clean shutdown
    await self.initialize() # Fresh start

# Service-specific cleanup
async def shutdown(self):
    """Cleanup before restart."""
    await disconnect_hardware()
    cancel_background_tasks()
    clear_caches()
```

## Related Decisions

- Tag caching strategy
- Hardware connection management
- Config validation approach
