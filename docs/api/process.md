# Process Service API Documentation

REST API for managing process execution, patterns, parameters, and sequences.

**Base URL**: `/process`  
**Port**: 8004

## Health Check

### GET /health

Get service health status.

**Response**:

```json
{
    "status": "ok|error",
    "service": "process",
    "version": "1.0.0",
    "is_running": true,
    "uptime": 123.45,
    "error": null,
    "components": {
        "parameter": {
            "status": "ok",
            "error": null
        },
        "pattern": {
            "status": "ok",
            "error": null
        },
        "sequence": {
            "status": "ok",
            "error": null
        }
    }
}
```

## Nozzle Management

### GET /nozzles

List available nozzles.

**Response**:

```json
{
    "nozzles": [
        {
            "name": "nozzle-01",
            "type": "convergent-divergent",
            "throat_diameter": 0.5,
            "exit_diameter": 2.0,
            "length": 100.0
        }
    ]
}
```

### GET /nozzles/{nozzle_id}

Get nozzle by ID.

**Parameters**:

- `nozzle_id`: Nozzle identifier

**Response**:

```json
{
    "nozzle": {
        "name": "nozzle-01",
        "type": "convergent-divergent",
        "throat_diameter": 0.5,
        "exit_diameter": 2.0,
        "length": 100.0
    }
}
```

## Powder Management

### GET /powders

List available powders.

**Response**:

```json
{
    "powders": [
        {
            "name": "powder-01",
            "material": "Cu",
            "size_range": {
                "min": 0.1,
                "max": 1.0
            },
            "morphology": "spherical"
        }
    ]
}
```

### GET /powders/{powder_id}

Get powder by ID.

**Parameters**:

- `powder_id`: Powder identifier

**Response**:

```json
{
    "powder": {
        "name": "powder-01",
        "material": "Cu",
        "size_range": {
            "min": 0.1,
            "max": 1.0
        },
        "morphology": "spherical"
    }
}
```

## Pattern Management

### GET /patterns

List available patterns.

**Response**:

```json
{
    "patterns": [
        {
            "id": "pattern-01",
            "name": "Linear Pattern",
            "description": "Simple linear pattern",
            "type": "linear",
            "params": {
                "width": 100.0,
                "height": 50.0,
                "velocity": 30.0,
                "line_spacing": 2.0
            }
        }
    ]
}
```

### POST /patterns/generate

Generate new pattern.

**Request**:

```json
{
    "pattern": {
        "name": "New Pattern",
        "description": "Pattern description",
        "type": "linear",
        "params": {
            "width": 100.0,
            "height": 50.0,
            "velocity": 30.0,
            "line_spacing": 2.0
        }
    }
}
```

**Response**:

```json
{
    "message": "Pattern generated successfully",
    "pattern_id": "pattern-01"
}
```

## Parameter Management

### GET /parameters

List available parameter sets.

**Response**:

```json
{
    "parameter_sets": [
        {
            "name": "params-01",
            "created": "2024-01-01",
            "author": "John Doe",
            "description": "Test parameters",
            "nozzle": "nozzle-01",
            "main_gas": 50.0,
            "feeder_gas": 10.0,
            "frequency": 500.0,
            "deagglomerator_speed": 35.0
        }
    ]
}
```

### POST /parameters/generate

Generate new parameter set.

**Request**:

```json
{
    "process": {
        "name": "New Parameters",
        "author": "John Doe",
        "description": "Parameter description",
        "nozzle": "nozzle-01",
        "main_gas": 50.0,
        "feeder_gas": 10.0,
        "frequency": 500.0,
        "deagglomerator_speed": 35.0
    }
}
```

**Response**:

```json
{
    "message": "Parameter set generated successfully",
    "parameter_id": "params-01"
}
```

## Sequence Management

### GET /sequences

List available sequences.

**Response**:

```json
{
    "sequences": [
        {
            "id": "sequence-01",
            "metadata": {
                "name": "Test Sequence",
                "version": "1.0.0",
                "created": "2024-01-01",
                "author": "John Doe",
                "description": "Test sequence"
            },
            "steps": [
                {
                    "name": "Initialize",
                    "description": "Initialize system",
                    "action_group": "initialize"
                },
                {
                    "name": "Pattern 1",
                    "description": "Execute pattern",
                    "pattern": "pattern-01",
                    "parameters": "params-01"
                }
            ]
        }
    ]
}
```

### POST /sequences/{sequence_id}/start

Start sequence execution.

**Parameters**:

- `sequence_id`: Sequence identifier

**Response**:

```json
{
    "message": "Sequence started successfully"
}
```

### POST /sequences/{sequence_id}/stop

Stop sequence execution.

**Parameters**:

- `sequence_id`: Sequence identifier

**Response**:

```json
{
    "message": "Sequence stopped successfully"
}
```

### GET /sequences/{sequence_id}/status

Get sequence execution status.

**Parameters**:

- `sequence_id`: Sequence identifier

**Response**:

```json
{
    "sequence_id": "sequence-01",
    "status": "running|stopped|error",
    "current_step": 1,
    "total_steps": 5,
    "error": null
}
```

### WebSocket /sequences/ws/{sequence_id}

Real-time sequence status updates.

**Parameters**:

- `sequence_id`: Sequence identifier

**Messages**:

```json
{
    "type": "sequence_status",
    "data": {
        "sequence_id": "sequence-01",
        "status": "running",
        "current_step": 1,
        "total_steps": 5,
        "error": null
    }
}
```

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request

```json
{
    "status": "error",
    "message": "Invalid request parameters"
}
```

### 404 Not Found

```json
{
    "status": "error",
    "message": "Resource not found"
}
```

### 409 Conflict

```json
{
    "status": "error",
    "message": "Resource state conflict"
}
```

### 422 Validation Error

```json
{
    "status": "error",
    "message": "Validation failed",
    "details": [
        {
            "loc": ["field_name"],
            "msg": "field error description"
        }
    ]
}
```

### 500 Internal Server Error

```json
{
    "status": "error",
    "message": "Internal server error"
}
```

### 503 Service Unavailable

```json
{
    "status": "error",
    "message": "Service not available"
}
```
