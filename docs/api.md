# API Documentation

## UI Service (Port 8000)

## Configuration Service (Port 8001)

### GET /config/list

List available configurations.

```json
{
  "configs": ["config1", "config2"]
}
```

### GET /config/{name}

Get configuration by name.

```json
{
  "name": "config1",
  "data": {},
  "format": "yaml"
}
```

### PUT /config/{name}

Update configuration.

```json
{
  "data": {},
  "format": "yaml"
}
```

Response:

```json
{
  "message": "Configuration {name} updated successfully"
}
```

### POST /config/validate/{name}

Validate configuration against schema.

```json
{
  "data": {},
  "format": "yaml"
}
```

Response:

```json
{
  "message": "Configuration {name} is valid"
}
```

### GET /config/schema/list

List available schemas (read-only).

```json
{
  "schemas": ["schema1", "schema2"]
}
```

### GET /config/schema/{name}

Get schema definition (read-only).

```json
{
  "name": "schema1",
  "schema_definition": {}
}
```

## State Service (Port 8002)

### GET /state

Get current state.

```json
{
  "state": "idle",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### GET /transitions

Get valid state transitions.

```json
{
  "idle": ["running", "error"],
  "running": ["idle", "error"],
  "error": ["idle"]
}
```

### POST /transition/{new_state}

Transition to new state.

```json
{
  "message": "Transitioned to {new_state}",
  "previous_state": "idle",
  "current_state": "running"
}
```

### GET /history

Get state history.

```json
[
  {
    "state": "idle",
    "timestamp": "2024-01-01T00:00:00.000Z"
  }
]
```

## Communication Service (Port 8003)

### WebSocket Endpoints

#### WS /ws/state

Real-time system state updates.

```json
{
  "type": "state_update",
  "data": {
    "equipment": {
      "gas": {
        "main_flow": 0.0,
        "main_flow_measured": 0.0,
        "feeder_flow": 0.0,
        "feeder_flow_measured": 0.0,
        "main_valve": false,
        "feeder_valve": false
      },
      "vacuum": {
        "chamber_pressure": 0.0,
        "gate_valve": false,
        "mech_pump": false,
        "booster_pump": false,
        "vent_valve": false
      },
      "feeder": {
        "running": false,
        "frequency": 0.0
      },
      "deagglomerator": {
        "duty_cycle": 35.0
      },
      "nozzle": {
        "active_nozzle": 1,
        "shutter_open": false
      },
      "pressure": {
        "chamber": 0.0,
        "feeder": 0.0,
        "main_supply": 0.0,
        "nozzle": 0.0,
        "regulator": 0.0
      },
      "motion": {
        "position": {
          "x": 0.0,
          "y": 0.0,
          "z": 0.0
        },
        "status": {
          "x_axis": {
            "position": 0.0,
            "in_position": true,
            "moving": false,
            "error": false,
            "homed": true
          },
          "y_axis": {
            "position": 0.0,
            "in_position": true,
            "moving": false,
            "error": false,
            "homed": true
          },
          "z_axis": {
            "position": 0.0,
            "in_position": true,
            "moving": false,
            "error": false,
            "homed": true
          },
          "module_ready": true
        }
      },
      "hardware": {
        "motion_enabled": true,
        "plc_connected": true,
        "position_valid": true
      },
      "process": {
        "gas_flow_stable": true,
        "powder_feed_active": false,
        "process_ready": true
      },
      "safety": {
        "emergency_stop": false,
        "interlocks_ok": true,
        "limits_ok": true
      }
    }
  }
}
```

### Gas Control

#### POST /gas/main/flow

Set main gas flow rate.

```json
{
  "flow_rate": 50.0
}
```

#### POST /gas/feeder/flow

Set feeder gas flow rate.

```json
{
  "flow_rate": 25.0
}
```

#### POST /gas/main/valve

Control main gas valve.

```json
{
  "open": true
}
```

#### POST /gas/feeder/valve

Control feeder gas valve.

```json
{
  "open": true
}
```

### Feeder Control

#### POST /feeder/{feeder_id}/frequency

Set feeder frequency.

```json
{
  "frequency": 500
}
```

#### POST /feeder/{feeder_id}/start

Start feeder.

#### POST /feeder/{feeder_id}/stop

Stop feeder.

### Deagglomerator Control

#### POST /deagg/{deagg_id}/speed

Set deagglomerator speed.

```json
{
  "speed": 50
}
```

#### POST /deagg/{deagg_id}/set

Set complete deagglomerator parameters.

```json
{
  "duty_cycle": 35,
  "frequency": 500
}
```

### Nozzle Control

#### POST /nozzle/select

Select active nozzle.

```json
{
  "nozzle_id": 1
}
```

#### POST /nozzle/shutter/open

Open nozzle shutter.

#### POST /nozzle/shutter/close

Close nozzle shutter.

### Vacuum Control

#### POST /vacuum/gate

Control gate valve position.

```json
{
  "position": "open"
}
```

#### POST /vacuum/vent/open

Open vent valve.

#### POST /vacuum/vent/close

Close vent valve.

#### POST /vacuum/mech/start

Start mechanical pump.

#### POST /vacuum/mech/stop

Stop mechanical pump.

#### POST /vacuum/booster/start

Start booster pump.

#### POST /vacuum/booster/stop

Stop booster pump.

### Motion Control

#### POST /motion/jog/{axis}

Perform relative move on single axis.

```json
{
  "distance": 10.0,
  "velocity": 50.0
}
```

#### POST /motion/move

Execute coordinated move to target position.

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

Set current position as home.

#### POST /motion/home/move

Move to home position.

### Process Service (Port 8004)

### Sequence Endpoints

#### GET /process/sequences

List available sequences.

```json
{
  "message": "Retrieved N sequences",
  "sequences": [
    {
      "id": "sequence1",
      "metadata": {
        "name": "Test Sequence",
        "version": "1.0.0",
        "created": "2024-01-01",
        "author": "John Doe",
        "description": "A test sequence"
      },
      "steps": [
        {
          "name": "Initialize",
          "description": "Initialize system",
          "action_group": "initialize",
          "actions": null
        },
        {
          "name": "Pattern 1",
          "description": "First pattern",
          "action_group": null,
          "actions": [
            {
              "action_group": "move_to_start",
              "parameters": {
                "x": 0.0,
                "y": 0.0,
                "z": 50.0
              }
            },
            {
              "action_group": "execute_pattern",
              "parameters": {
                "pattern_id": "pattern1",
                "passes": 3
              }
            }
          ]
        }
      ],
      "created_at": "2024-01-01T00:00:00.000Z",
      "updated_at": "2024-01-01T00:00:00.000Z"
    }
  ]
}
```

#### GET /process/sequences/{sequence_id}

Get sequence by ID.

```json
{
  "message": "Retrieved sequence {id}",
  "sequence": {
    "id": "sequence1",
    "name": "Test Sequence",
    "description": "A test sequence"
  }
}
```

#### POST /process/sequences/{sequence_id}/start

Start sequence execution.

```json
{
  "message": "Started sequence {id}",
  "status": "running"
}
```

#### POST /process/sequences/{sequence_id}/stop

Stop sequence execution.

```json
{
  "message": "Stopped sequence {id}",
  "status": "stopped"
}
```

#### GET /process/sequences/{sequence_id}/status

Get sequence execution status.

```json
{
  "message": "Status for sequence {id}: {status}",
  "status": "running|stopped|error"
}
```

### Pattern Endpoints

#### GET /process/patterns

List available patterns.

```json
{
  "message": "Retrieved N patterns",
  "patterns": [
    {
      "id": "pattern1",
      "name": "Test Pattern",
      "description": "A test pattern"
    }
  ]
}
```

### Parameter Endpoints

#### GET /process/parameters

List available parameter sets.

```json
{
  "message": "Retrieved N parameter sets",
  "parameter_sets": [
    {
      "id": "params1",
      "name": "Test Parameters",
      "description": "Test parameter set"
    }
  ]
}
```

### Data Collection Service (Port 8005)

#### POST /data_collection/data/start/{sequence_id}

Start data collection for a sequence.

```json
{
  "message": "Data collection started"
}
```

#### POST /data_collection/data/stop

Stop current data collection.

```json
{
  "message": "Data collection stopped"
}
```

#### POST /data_collection/data/record

Record a spray event.

```json
{
  "message": "Event recorded successfully",
  "event": {
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
}
```

## Validation Service (Port 8006)

### POST /validation/hardware

Validate hardware configuration.

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### POST /validation/parameter/{parameter_type}

Validate parameter configuration.

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### POST /validation/pattern/{pattern_type}

Validate pattern configuration.

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

### POST /validation/sequence

Validate sequence configuration.

```json
{
  "valid": true,
  "errors": [],
  "warnings": []
}
```

## Health Endpoints

All services expose a health endpoint:

### GET /health

```json
{
  "status": "ok|error",
  "service": "service_name",
  "version": "1.0.0",
  "is_running": true,
  "uptime": 123.45,
  "error": null,
  "components": {
    "component1": {
      "status": "ok|error",
      "error": null
    }
  }
}
```
