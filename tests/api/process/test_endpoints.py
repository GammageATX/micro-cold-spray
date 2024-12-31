"""Tests for process API endpoints."""

import pytest
import yaml
from pathlib import Path
from fastapi.testclient import TestClient

from micro_cold_spray.api.process.process_app import create_process_service


@pytest.fixture(autouse=True)
def setup_data_dirs():
    """Create required data directories."""
    dirs = [
        "data/sequences",
        "data/patterns",
        "data/parameters",
        "data/nozzles",
        "data/powders"
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    yield


@pytest.fixture
async def client():
    """Create test client with initialized service."""
    app = create_process_service()
    
    # Initialize and start service before tests
    await app.state.service.initialize()
    await app.state.service.start()
    
    # Create test client
    client = TestClient(app)
    
    yield client
    
    # Cleanup after tests
    if app.state.service.is_running:
        await app.state.service.stop()


@pytest.mark.asyncio
async def test_list_patterns(client):
    """Test pattern listing endpoint."""
    response = client.get("/process/patterns/list")
    assert response.status_code == 200
    data = response.json()
    assert "patterns" in data
    assert isinstance(data["patterns"], list)


@pytest.mark.asyncio
async def test_list_parameters(client):
    """Test parameter listing endpoint."""
    response = client.get("/process/parameters/list")
    assert response.status_code == 200
    data = response.json()
    assert "parameter_sets" in data
    assert isinstance(data["parameter_sets"], list)


@pytest.mark.asyncio
async def test_generate_pattern(client):
    """Test pattern generation endpoint."""
    # First create the pattern file
    pattern_data = {
        "pattern": {
            "id": "test_pattern",
            "name": "Test Pattern",
            "description": "A test pattern",
            "type": "serpentine",
            "params": {
                "width": 100.0,
                "height": 50.0,
                "z_height": 10.0,
                "velocity": 30.0,
                "line_spacing": 2.0,
                "direction": "x"
            }
        }
    }
    
    pattern_file = Path("data/patterns/test_pattern.yaml")
    with open(pattern_file, "w") as f:
        yaml.dump(pattern_data, f)
    
    # Then test the endpoint
    response = client.post("/process/patterns/generate", json=pattern_data)
    assert response.status_code == 200
    data = response.json()
    assert "pattern_id" in data


def test_generate_parameter_set(client):
    """Test parameter set generation endpoint."""
    param_data = {
        "process": {
            "name": "Test Parameters",
            "created": "2024-03-20",
            "author": "Test User",
            "description": "Test parameter set",
            "nozzle": "MCS-24",
            "main_gas": 50.0,
            "feeder_gas": 5.0,
            "frequency": 600,
            "deagglomerator_speed": 25
        }
    }
    
    response = client.post("/process/parameters/generate", json=param_data)
    assert response.status_code == 200
    data = response.json()
    assert "parameter_id" in data


def test_sequence_execution(client):
    """Test sequence execution endpoints."""
    sequence_data = {
        "sequence": {
            "metadata": {
                "name": "Test Sequence",
                "version": "1.0",
                "created": "2024-03-20",
                "author": "Test User",
                "description": "Test sequence"
            },
            "steps": [
                {
                    "name": "Initialize",
                    "step_type": "initialize",
                    "description": "Initialize system"
                },
                {
                    "name": "Test Pattern",
                    "step_type": "pattern",
                    "description": "Run pattern",
                    "pattern_id": "test_pattern",
                    "parameters": {
                        "main_gas": 50.0,
                        "feeder_gas": 5.0
                    }
                }
            ]
        }
    }
    
    # Generate sequence
    response = client.post("/process/sequences/generate", json=sequence_data)
    assert response.status_code == 200
    data = response.json()
    sequence_id = data["sequence_id"]
    
    # Start sequence
    response = client.post(f"/process/sequences/{sequence_id}/start")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    
    # Get sequence status
    response = client.get(f"/process/sequences/{sequence_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    
    # Stop sequence
    response = client.post(f"/process/sequences/{sequence_id}/stop")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data


def test_pattern_validation(client):
    """Test pattern validation."""
    # Invalid pattern (missing required fields)
    invalid_pattern = {
        "id": "invalid_pattern",
        "name": "Invalid Pattern"
        # Missing type and params
    }
    
    response = client.post("/process/patterns/generate", json=invalid_pattern)
    assert response.status_code == 422
    
    # Invalid parameters (out of range)
    invalid_params = {
        "id": "invalid_params",
        "name": "Invalid Parameters",
        "type": "serpentine",
        "params": {
            "width": 1000.0,  # Too large
            "height": -50.0,  # Negative
            "line_spacing": 0.05  # Too small
        }
    }
    
    response = client.post("/process/patterns/generate", json=invalid_params)
    assert response.status_code == 422


def test_parameter_validation(client):
    """Test parameter validation."""
    # Invalid parameters (out of range)
    invalid_params = {
        "process": {
            "name": "Invalid Parameters",
            "created": "2024-03-20",
            "author": "Test User",
            "description": "Invalid parameter set",
            "nozzle": "MCS-24",
            "main_gas": 150.0,  # Too high
            "feeder_gas": -5.0,  # Negative
            "frequency": 2000,   # Too high
            "deagglomerator_speed": 150  # Too high
        }
    }
    
    response = client.post("/process/parameters/generate", json=invalid_params)
    assert response.status_code == 422
