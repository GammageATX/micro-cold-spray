# Process API

The Process API provides endpoints for managing spray process execution.

Base URL: `/process`

## Endpoints

### Health Check

``` curl
GET /health
```

Returns service health status.

### Parameters

``` curl
GET /parameters
GET /parameters/{param_id}
POST /parameters/generate
PUT /parameters/{param_id}
```

Manage spray parameter sets.

### Patterns

``` curl
GET /patterns
POST /patterns/generate
```

Manage spray patterns.

### Sequences

``` curl
GET /sequences
POST /sequences/{sequence_id}/start
GET /sequences/{sequence_id}/status
```

Manage spray sequences.

### Nozzles

``` curl
GET /nozzles
GET /nozzles/{nozzle_id}
```

Manage spray nozzles.

### Powders

``` curl
GET /powders
GET /powders/{powder_id}
```

Manage spray powders.
