# API Standardization Guide

## 1. Service Class Structure

### Initialization Pattern

- ****init****
  - Set basic properties only: _service_name, _version,_is_running,_start_time,_config
  - Initialize component services to None
  - No config loading, no component creation
  - End with logger.info(f"{self._service_name} service initialized")

- **initialize()**
  - Load config if needed
  - Update version from config
  - Create component services
  - Initialize components in dependency order
  - Proper error handling with create_error
  - End with logger.info(f"{self.service_name} service initialized")

- **start()**
  - Check if already running (409 Conflict)
  - Check if components initialized (400 Bad Request)
  - Start components in dependency order
  - Set _is_running = True and _start_time = datetime.now() at end
  - End with logger.info(f"{self.service_name} service started")

### Stop Method Pattern

- **stop()**

  ```python
  async def stop(self) -> None:
      """Stop service."""
      try:
          if not self.is_running:
              raise create_error(
                  status_code=status.HTTP_409_CONFLICT,
                  message=f"{self.service_name} service not running"
              )

          # 1. Unregister from external services first
          if self._tag_cache:
              self._tag_cache.remove_state_callback(self._handle_state_change)

          # 2. Clear internal callbacks and event handlers
          self._state_callbacks.clear()

          # 3. Reset service state
          self._is_running = False
          self._start_time = None

          logger.info(f"{self.service_name} service stopped")

      except Exception as e:
          error_msg = f"Failed to stop {self.service_name} service: {str(e)}"
          logger.error(error_msg)
          raise create_error(
              status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
              message=error_msg
          )
  ```

  **Key Points:**
  1. Check running state first (409 if not running)
  2. Clean up in reverse dependency order:
     - Unregister from external services first
     - Clear internal callbacks/handlers
     - Reset service state last
  3. Log success
  4. Proper error handling with 503 on failure
  5. No state changes on error

### Required Properties

- **Base Properties**

  ```python
  self._service_name: str  # Service identifier
  self._version: str = "1.0.0"  # Updated from config
  self._is_running: bool = False
  self._start_time: Optional[datetime] = None
  self._config: Optional[Dict[str, Any]] = None
  ```

- **Standard Properties**

  ```python
  @property
  def service_name(self) -> str:
      return self._service_name

  @property
  def version(self) -> str:
      return self._version

  @property
  def is_running(self) -> bool:
      return self._is_running

  @property
  def uptime(self) -> float:
      return (datetime.now() - self._start_time).total_seconds() if self._start_time else 0.0
  ```

## 2. Health Check Implementation

### Health Method Pattern

```python
async def health(self) -> ServiceHealth:
    try:
        # Get health from components
        component_healths = await gather_component_health()
        
        # Build component statuses
        components = {
            name: ComponentHealth(
                status=health.status,
                error=health.error
            ) for name, health in component_healths.items()
        }
        
        # Overall status is error if any component is in error
        overall_status = "error" if any(c.status == "error" for c in components.values()) else "ok"
        
        return ServiceHealth(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            is_running=self.is_running,
            uptime=self.uptime,
            error=None if overall_status == "ok" else "One or more components in error state",
            components=components
        )
        
    except Exception as e:
        error_msg = f"Health check failed: {str(e)}"
        logger.error(error_msg)
        return ServiceHealth(
            status="error",
            service=self.service_name,
            version=self.version,
            is_running=False,
            uptime=self.uptime,
            error=error_msg,
            components={name: ComponentHealth(status="error", error=error_msg) for name in self._component_names}
        )
```

## 3. Error Handling

### Standard Error Pattern

```python
try:
    # Operation code
except Exception as e:
    error_msg = f"Failed to {operation} {self.service_name} service: {str(e)}"
    logger.error(error_msg)
    raise create_error(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,  # Or appropriate code
        message=error_msg
    )
```

### Status Codes

- 400 Bad Request: Service not initialized, invalid parameters
- 409 Conflict: Service state conflicts (already running/not running)
- 503 Service Unavailable: Operation failed, service unhealthy

## 4. Component Management

### Component Initialization

- Components initialized to None in **init**
- Created and initialized in initialize()
- Started in dependency order
- Stopped in reverse order

### Component Health

- Each component provides health status
- Parent service aggregates component health
- Use ComponentHealth model consistently
- Status values: "ok" or "error" only
