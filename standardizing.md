# API Standardization Guide

## 1. Service Class Structure

- **Common Base Properties**
  - `_version` - Service version from config
  - `_is_running` - Running state flag
  - `_start_time` - Service start timestamp

- **Standard Lifecycle Methods**
  - `__init__()` - Basic initialization
  - `initialize()` - Async setup
  - `start()` - Start service
  - `stop()` - Stop service

- **Standard Properties**
  - `version` - Service version from config
  - `is_running` - Service state
  - `uptime` - Service uptime

## 2. FastAPI Factory Pattern

- **Factory Function**
  - Each API must have `create_*_service()` factory
  - Service instances stored in `app.state`

- **Standard Setup**
  - CORS middleware configuration
  - Standard exception handlers
  - Health check endpoint at `/health`

- **Event Handlers**
  - `startup` - Initialize and start services in dependency order
  - `shutdown` - Stop services in reverse order

## 3. Configuration Management

- **Config Files**
  - Each service has its own YAML config file
  - Standard location: `config/{service_name}.yaml`
  - Version specified in config file

- **Config Structure**
  - Service-level settings (host, port, etc)
  - Component-specific settings
  - Version information for service and components

- **Config Loading**
  - Load in factory function
  - Pass to service constructors
  - Support optional config override in factory

## 4. Health Check Implementation

- **Standard Models**
  - Use `ServiceHealth` from `utils.health`
  - Use `ComponentHealth` for sub-components
  - Consistent status values: "ok", "error"

- **Health Method**
  - Each service must implement `health()` method
  - Return `ServiceHealth` with component status
  - Include version, uptime, and running state
  - Aggregate component health for overall status

- **Health Endpoint**
  - GET `/health` endpoint in each API
  - Returns `ServiceHealth` model
  - Aggregates health from all sub-services
  - Uses shortest uptime as service uptime

## 5. Error Handling

- **Error Creation**
  - Use `create_error` from `utils.errors`
  - Include appropriate status code and message
  - Add details when relevant

- **Standard Status Codes**
  - 400 Bad Request - Invalid input
  - 404 Not Found - Resource not found
  - 409 Conflict - Resource state conflict
  - 422 Unprocessable Entity - Validation error
  - 500 Internal Server Error - Unexpected error
  - 503 Service Unavailable - Service not ready

- **Error Response Format**
  - Use `ErrorResponse` model consistently
  - Include status code and message
  - Add error details when available
  - Proper error logging before raising

## 6. Logging

- **Logger Usage**
  - Use `loguru` consistently
  - Standard log levels
  - Structured logging where appropriate

- **Log Format**
  - Standard message format
  - Key lifecycle event logging
  - Error context and stack traces

## 7. State Management

- **Service State**
  - Clear state transitions
  - Proper cleanup on stop
  - State stored in service instances

- **FastAPI State**
  - Services stored in `app.state`
  - Clear dependency order
  - Proper async handling
