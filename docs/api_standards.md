# API Standards

## Endpoint Structure

### Health Endpoints

All services expose a health endpoint at the root level:
```
GET /health
```
- Returns 200 OK if service is healthy
- Returns 503 Service Unavailable if service is not running
- No prefix, always at root level
- Standard response format:
```json
{
    "status": "ok",
    "service_name": "service_name",
    "version": "1.0.0",
    "is_running": true,
    "message": "Service is healthy",
    "error": null,
    "uptime": "1h 23m 45s"
}
```

### Service-Specific Endpoints

Service endpoints follow this pattern:
```
/{service_name}/{resource}/{action}
```

Example:
```
/communication/equipment/status
/messaging/publish/{topic}
/config/application
```

## Response Formats

### Success Response

```json
{
    "status": "ok",
    "message": "Operation successful",
    "timestamp": "2024-12-18T15:26:23.972Z",
    "data": {
        // Operation-specific data
    }
}
```

### Error Response

```json
{
    "status": "error",
    "message": "Error description",
    "error_code": "ERROR_CODE",
    "timestamp": "2024-12-18T15:26:23.972Z",
    "context": {
        // Error-specific context
    }
}
```

## HTTP Status Codes

- 200 OK: Successful operation
- 400 Bad Request: Client error (validation, invalid input)
- 404 Not Found: Resource not found
- 409 Conflict: Resource state conflict
- 422 Unprocessable Entity: Validation error
- 500 Internal Server Error: Server error
- 503 Service Unavailable: Service not running/ready

## Service-Specific Endpoints

### Config Service (Port 8001)

```
GET /config/{config_type}      # Get configuration
PUT /config/{config_type}      # Update configuration
GET /config/schema/{type}      # Get config schema
```

### Messaging Service (Port 8002)

```
POST /messaging/publish/{topic}     # Publish message
WS   /messaging/subscribe/{topic}   # Subscribe to topic
```

### Communication Service (Port 8003)

```
GET  /communication/equipment/status    # Get equipment status
POST /communication/equipment/control   # Control equipment
GET  /communication/motion/status      # Get motion status
POST /communication/motion/control     # Control motion
```

### State Service (Port 8004)

```
GET  /state/current              # Get current state
POST /state/transition          # Request state transition
GET  /state/history            # Get state history
```

### Data Collection Service (Port 8005)

```
GET  /data/tags/{tag_path}     # Get tag data
POST /data/collection/start    # Start data collection
POST /data/collection/stop     # Stop data collection
```

## Common Headers

```
Content-Type: application/json
Accept: application/json
```

## Authentication

Currently using internal network security. Future versions may add:
- API key authentication
- JWT tokens
- Role-based access control

## Rate Limiting

Currently no rate limiting implemented. Consider adding:
- Per-client rate limits
- Service-specific limits
- Burst allowances