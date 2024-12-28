# API Standardization Guide

## 1. Service Class Structure

### FastAPI Application Creation Pattern

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
from pathlib import Path
import yaml
from typing import Dict, Any

def load_config() -> Dict[str, Any]:
    """Load service configuration.
    
    Returns:
        Dict[str, Any]: Configuration dictionary
        
    Raises:
        FileNotFoundError: If config file not found
    """
    config_path = Path("config/service.yaml")
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
        
    with open(config_path) as f:
        return yaml.safe_load(f)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle startup and shutdown events."""
    try:
        logger.info("Starting service...")
        
        # Get service from app state
        service = app.state.service
        
        # Initialize and start service
        await service.initialize()
        await service.start()
        
        logger.info("Service started successfully")
        
        yield  # Server is running
        
        # Shutdown
        if service.is_running:
            await service.stop()
            logger.info("Service stopped successfully")
            
    except Exception as e:
        logger.error(f"Service startup failed: {e}")
        # Don't raise here - let the service start in degraded mode
        # The health check will show which components failed
        yield
        # Still try to stop service if it exists
        if hasattr(app.state, "service") and app.state.service.is_running:
            try:
                await app.state.service.stop()
            except Exception as stop_error:
                logger.error(f"Failed to stop service: {stop_error}")

def create_service() -> FastAPI:
    """Create and configure the FastAPI application."""
    # Load config
    config = load_config()
    version = config.get("version", "1.0.0")
    
    app = FastAPI(
        title="Service Name",
        description="Service description",
        version=version,
        lifespan=lifespan
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Add error handlers
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Handle validation errors."""
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    # Create service with config
    service = ServiceClass(config)
    app.state.service = service

    # Add routes
    app.include_router(service_router)

    @app.get("/health", response_model=ServiceHealth)
    async def health_check() -> ServiceHealth:
        """Get service health status."""
        return await app.state.service.health()

    return app

### Service Initialization Pattern

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
- 422 Unprocessable Entity: Validation errors
- 503 Service Unavailable: Operation failed, service unhealthy

## 4. Component Management

### Component Initialization

1. **Client Creation**
   - Create external clients first (PLC, SSH, etc.)
   - Handle mock/real client selection based on config
   - Initialize with required credentials/settings

2. **Service Creation Order**
   - Create services in dependency order
   - Pass required dependencies in constructor
   - Example:

     ```python
     # Create clients first
     plc_client = create_plc_client(config)
     ssh_client = create_ssh_client(config)

     # Create services in dependency order
     tag_mapping = TagMappingService(config)
     tag_cache = TagCacheService(config, plc_client, ssh_client, tag_mapping)
     motion = MotionService(config, tag_cache)
     equipment = EquipmentService(config, tag_cache)
     ```

3. **Initialization Flow**
   - Initialize base service first
   - Initialize components in dependency order
   - Handle initialization failures gracefully
   - Example:

     ```python
     async def initialize(self):
         """Initialize service and components."""
         try:
             # Initialize base service
             await self._load_config()
             
             # Initialize components in order
             await self._tag_mapping.initialize()
             await self._tag_cache.initialize()
             await self._motion.initialize()
             await self._equipment.initialize()
             
             logger.info(f"{self.service_name} initialized")
             
         except Exception as e:
             error_msg = f"Failed to initialize {self.service_name}: {str(e)}"
             logger.error(error_msg)
             raise create_error(
                 status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                 message=error_msg
             )
     ```

4. **Dependency Management**
   - Clear separation between required and optional dependencies
   - Document dependencies in class docstring
   - Handle missing optional dependencies gracefully
   - Example:

     ```python
     class ServiceClass:
         """Service class with dependencies.
         
         Required Dependencies:
             - config: Service configuration
             - tag_cache: Tag cache service for data access
             
         Optional Dependencies:
             - ssh_client: SSH client for remote access
             - metrics: Metrics collection service
         """
         
         def __init__(
             self,
             config: Dict[str, Any],
             tag_cache: TagCacheService,
             ssh_client: Optional[SSHClient] = None,
             metrics: Optional[MetricsService] = None
         ):
             self._config = config
             self._tag_cache = tag_cache
             self._ssh_client = ssh_client
             self._metrics = metrics
     ```

### Self-Healing Behavior

Components should implement self-healing behavior to maintain stability:

1. Error Tracking
   - Track failed components separately (e.g. self._failed_components)
   - Keep detailed error information for each failure
   - Continue running with partial functionality when possible

2. Recovery Process
   - Attempt recovery during health checks
   - Reload failed components without impacting working ones
   - Log recovery attempts and results
   - Remove from failed tracking if recovery succeeds

3. Health Reporting
   - Report partial functionality over complete failure
   - Include failed component details in health status
   - Overall status "ok" if core functionality works
   - List specific failed components and their errors

4. Implementation Example:

   ```python
   # Track failures
   self._failed_components = {}
   
   # Recovery attempt
   async def _attempt_recovery(self):
       if self._failed_components:
           logger.info(f"Attempting recovery of {len(self._failed_components)} components...")
           # Try reloading each failed component
           
   # Health check
   async def health(self):
       # Try recovery first
       await self._attempt_recovery()
       
       # Report working and failed components
       components = {
           "working": ComponentHealth(...),
           "failed": ComponentHealth(
               status="error",
               error=f"Failed components: {list(self._failed_components.keys())}"
           )
       }
   ```
