# API Exception Handling

## Status
Proposed

## Context
As we migrate functionality from the core project into separate APIs, we need a plan for handling exceptions. The core project currently has a well-structured exception hierarchy in `exceptions.py` that we want to preserve while moving to APIs.

Current Exception Classes:
```python
CoreError              # Base exception
├── ValidationError    # Validation operations
├── OperationError     # Process operations
├── HardwareError     # Hardware communication
├── ConfigurationError # Configuration handling
├── StateError        # State management
├── MessageError      # Message broker
└── UIError           # UI operations
```

## Decision
We will migrate exceptions to their respective APIs as we create them, following these principles:

1. Exception Migration Map:
   - State API: `StateError`
   - Communication API: `HardwareError`
   - Process API: `OperationError`
   - Validation API: `ValidationError`
   - Config API: `ConfigurationError`
   - Messaging API: `MessageError`
   - UI: Will be replaced with new UI framework exceptions

2. Exception Structure in Each API:
   ```python
   class APIError(Exception):
       """Base exception for API."""
       def __init__(self, message: str, context: dict | None = None):
           super().__init__(message)
           self.context = context if context is not None else {}

   class DomainError(APIError):
       """Domain-specific exceptions."""

   class ValidationError(APIError):
       """Validation-specific exceptions."""
   ```

3. Exception Handling Rules:
   - Each API handles its own exceptions
   - APIs don't expose core exceptions
   - Consistent error response format
   - Proper error context preservation
   - Clear error messages

4. Error Response Format:
   ```json
   {
     "error": "error_type",
     "message": "Human readable message",
     "context": {
       "additional": "error context",
       "details": "specific to error"
     },
     "timestamp": "ISO timestamp"
   }
   ```

## Migration Plan

1. Phase 1 - Current APIs:
   - State API: Migrate `StateError`
   - Communication API: Migrate `HardwareError`
   - Keep `exceptions.py` as reference

2. Phase 2 - Upcoming APIs:
   - Process API: Create from `OperationError`
   - Validation API: Create from `ValidationError`
   - Config API: Create from `ConfigurationError`
   - Messaging API: Create from `MessageError`

3. Phase 3 - UI Replacement:
   - Remove `UIError`
   - Implement new UI error handling
   - Clean up remaining core exceptions

## Consequences

### Positive
1. Clear ownership of exceptions
2. Consistent error handling across APIs
3. Better error isolation
4. Cleaner API boundaries
5. Easier testing and maintenance

### Negative
1. Need to maintain consistency across APIs
2. Temporary duplication during migration
3. Need to update error handling in clients

## Implementation Notes

1. HTTP Status Codes:
   ```python
   @router.post("/endpoint")
   async def endpoint():
       try:
           # Operation
       except DomainError as e:
           raise HTTPException(
               status_code=400,
               detail={"error": str(e), "context": e.context}
           )
   ```

2. Error Context:
   ```python
   try:
       await service.operation()
   except APIError as e:
       logger.error(f"Operation failed: {e}", extra=e.context)
       raise
   ```

3. Client Error Handling:
   ```python
   try:
       response = await api.request()
       if response.is_error:
           handle_error(response.error)
   except APIError as e:
       handle_api_error(e)
   ```

## References
- Original `exceptions.py`
- State API Implementation
- Communication API Implementation
- FastAPI Error Handling Docs 