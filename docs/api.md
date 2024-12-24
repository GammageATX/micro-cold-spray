# API Documentation

## Communication Service

Base URL: `http://localhost:8002`

### Motion Control

#### GET /motion/position

Get the current position of all axes.

Response:

```json
{
  "x": 0.0,
  "y": 0.0,
  "z": 0.0
}
```

#### GET /motion/status

Get the current motion system status.

Response:

```json
{
  "enabled": true,
  "homed": true,
  "error": false,
  "busy": false
}
```

#### POST /motion/jog/{axis}

Perform a relative move on a single axis.

Parameters:

- `axis`: Axis to jog (x, y, z)
- Request body:

```json
{
  "distance": 10.0,
  "velocity": 50.0
}
```

#### POST /motion/move

Execute a coordinated move to a target position.

Request body:

```json
{
  "x": 100.0,
  "y": 100.0,
  "z": 50.0,
  "velocity": 50.0,
  "wait_complete": true
}
```

#### POST /motion/home/set

Set the current position as home.

#### POST /motion/home/move

Move to the home position.

### Equipment Control

#### GET /equipment/state

Get the current state of all equipment.

Response:

```json
{
  "gas": {
    "main_flow": 0.0,
    "feeder_flow": 0.0,
    "main_pressure": 0.0,
    "feeder_pressure": 0.0,
    "nozzle_pressure": 0.0,
    "regulator_pressure": 0.0
  },
  "vacuum": {
    "chamber_pressure": 0.0,
    "mech_pump_running": false,
    "booster_pump_running": false,
    "vent_valve_open": false,
    "gate_valve_open": false
  },
  "feeders": [
    {
      "id": 1,
      "frequency": 200,
      "running": false
    },
    {
      "id": 2,
      "frequency": 200,
      "running": false
    }
  ],
  "deagglomerators": [
    {
      "id": 1,
      "duty_cycle": 35,
      "frequency": 500
    },
    {
      "id": 2,
      "duty_cycle": 35,
      "frequency": 500
    }
  ],
  "shutter": {
    "engaged": false
  }
}
```

#### POST /equipment/gas/main/flow

Set the main gas flow rate.

Request body:

```json
{
  "flow_rate": 50.0
}
```

#### POST /equipment/gas/feeder/flow

Set the feeder gas flow rate.

Request body:

```json
{
  "flow_rate": 25.0
}
```

#### POST /equipment/feeder/{feeder_id}/frequency

Set the feeder frequency.

Parameters:

- `feeder_id`: Feeder ID (1 or 2)
- Request body:

```json
{
  "frequency": 500
}
```

#### POST /equipment/feeder/{feeder_id}/start

Start a feeder.

Parameters:

- `feeder_id`: Feeder ID (1 or 2)

#### POST /equipment/feeder/{feeder_id}/stop

Stop a feeder.

Parameters:

- `feeder_id`: Feeder ID (1 or 2)

#### POST /equipment/deagg/{deagg_id}/speed

Set the deagglomerator speed.

Parameters:

- `deagg_id`: Deagglomerator ID (1 or 2)
- Request body:

```json
{
  "speed": 50
}
```

#### POST /equipment/vacuum/vent/open

Open the vent valve.

#### POST /equipment/vacuum/vent/close

Close the vent valve.

#### POST /equipment/vacuum/mech/start

Start the mechanical pump.

#### POST /equipment/vacuum/mech/stop

Stop the mechanical pump.

#### POST /equipment/vacuum/booster/start

Start the booster pump.

#### POST /equipment/vacuum/booster/stop

Stop the booster pump.

### Health Check

#### GET /health

Get the service health status.

Response:

```json
{
  "status": "ok",
  "service_name": "communication",
  "version": "1.0.0",
  "is_running": true,
  "uptime": 123.45,
  "error": null,
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

## Process Service

Base URL: `http://localhost:8003`

### Sequences

#### GET /process/sequences

List available sequences.

Response:

```json
[
  {
    "id": "sequence1",
    "name": "Test Sequence",
    "description": "A test sequence",
    "created_at": "2024-01-01T00:00:00.000Z",
    "updated_at": "2024-01-01T00:00:00.000Z"
  }
]
```

#### GET /process/sequences/{sequence_id}

Get sequence by ID.

Parameters:

- `sequence_id`: Sequence identifier

Response:

```json
{
  "id": "sequence1",
  "name": "Test Sequence",
  "description": "A test sequence",
  "created_at": "2024-01-01T00:00:00.000Z",
  "updated_at": "2024-01-01T00:00:00.000Z"
}
```

## Data Collection Service

Base URL: `http://localhost:8004`

### Data Collection

#### POST /data_collection/data/start/{sequence_id}

Start data collection for a sequence.

Parameters:

- `sequence_id`: Sequence identifier

#### POST /data_collection/data/stop

Stop current data collection.

#### POST /data_collection/data/record

Record a spray event.

Request body:

```json
{
  "sequence_id": "sequence1",
  "timestamp": "2024-01-01T00:00:00.000Z",
  "data": {
    "position": {
      "x": 0.0,
      "y": 0.0,
      "z": 0.0
    },
    "gas": {
      "main_flow": 50.0,
      "feeder_flow": 25.0
    }
  }
}
```

#### GET /data_collection/data/{sequence_id}

Get all events for a sequence.

Parameters:

- `sequence_id`: Sequence identifier

Response:

```json
[
  {
    "sequence_id": "sequence1",
    "timestamp": "2024-01-01T00:00:00.000Z",
    "data": {
      "position": {
        "x": 0.0,
        "y": 0.0,
        "z": 0.0
      },
      "gas": {
        "main_flow": 50.0,
        "feeder_flow": 25.0
      }
    }
  }
]
```

## Configuration Service

Base URL: `http://localhost:8005`

### Configuration Management

#### GET /config/{name}

Get configuration by name.

Parameters:

- `name`: Configuration name

Response:

```json
{
  "name": "config1",
  "data": {},
  "format": "yaml"
}
```

#### PUT /config/{name}

Update configuration.

Parameters:

- `name`: Configuration name
- Request body:

```json
{
  "data": {},
  "format": "yaml"
}
```

#### POST /config/validate/{name}

Validate configuration against schema.

Parameters:

- `name`: Configuration name
- Request body:

```json
{
  "data": {},
  "format": "yaml"
}
```

#### GET /config/schema/{name}

Get schema by name.

Parameters:

- `name`: Schema name

Response:

```json
{
  "name": "schema1",
  "schema_definition": {}
}
```

#### PUT /config/schema/{name}

Update schema.

Parameters:

- `name`: Schema name
- Request body:

```json
{
  "schema_definition": {}
}
```

## State Service

Base URL: `http://localhost:8006`

### State Management

#### GET /state

Get current state.

Response:

```json
{
  "state": "idle",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

#### GET /transitions

Get valid state transitions.

Response:

```json
{
  "idle": ["running", "error"],
  "running": ["idle", "error"],
  "error": ["idle"]
}
```

#### POST /transition/{new_state}

Transition to new state.

Parameters:

- `new_state`: Target state

#### GET /history

Get state history.

Query Parameters:

- `limit`: Maximum number of history entries to return

Response:

```json
[
  {
    "state": "idle",
    "timestamp": "2024-01-01T00:00:00.000Z"
  }
]
```

## Validation Service

Base URL: `http://localhost:8007`

### Validation

#### POST /validation/hardware

Validate hardware configuration.

Request body:

```json
{
  "hardware_config": {}
}
```

Response:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### POST /validation/parameter/{parameter_type}

Validate parameter configuration.

Parameters:

- `parameter_type`: Type of parameter to validate
- Request body:

```json
{
  "parameter_config": {}
}
```

Response:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### POST /validation/pattern/{pattern_type}

Validate pattern configuration.

Parameters:

- `pattern_type`: Type of pattern to validate
- Request body:

```json
{
  "pattern_config": {}
}
```

Response:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

#### POST /validation/sequence

Validate sequence configuration.

Request body:

```json
{
  "sequence_config": {}
}
```

Response:

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
