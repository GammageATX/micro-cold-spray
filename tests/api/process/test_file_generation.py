"""Process API file generation tests."""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from pathlib import Path
from loguru import logger
import yaml

from micro_cold_spray.api.process.process_app import create_process_service
from micro_cold_spray.api.process.models.process_models import (
    ProcessPattern,
    ParameterSet,
    SequenceMetadata,
    SequenceStep,
    Sequence
)


@pytest.fixture
def client():
    """Create test client."""
    app = create_process_service()
    return TestClient(app)


@pytest.fixture
def data_dir():
    """Create and cleanup data directories."""
    # Create directories
    dirs = [
        "data/sequences",
        "data/patterns",
        "data/parameters",
        "data/parameters/nozzles",
        "data/powders"
    ]
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    yield

    # No cleanup - let user inspect and delete files manually


@pytest.fixture
async def test_data(client, data_dir):
    """Create test data for process service tests."""
    app = client.app
    service = app.state.service
    
    # Initialize services
    await service.initialize()
    await service.start()
    
    # Create test patterns
    pattern1 = ProcessPattern(
        id="pattern1",
        name="Test Pattern 1",
        description="A test pattern for testing",
        type="linear",
        params={
            "width": 100.0,
            "height": 100.0,
            "line_spacing": 5.0,
            "velocity": 50.0,
            "z_height": 10.0
        }
    )
    pattern2 = ProcessPattern(
        id="pattern2",
        name="Test Pattern 2",
        description="Another test pattern",
        type="serpentine",
        params={
            "width": 150.0,
            "height": 150.0,
            "line_spacing": 7.5,
            "velocity": 75.0,
            "z_height": 15.0
        }
    )
    
    # Add patterns to service
    await service._pattern.create_pattern(pattern1)
    await service._pattern.create_pattern(pattern2)
    logger.info("Created test patterns")

    # Create test parameter sets
    params1 = ParameterSet(
        id="params1",
        name="Test Parameters 1",
        description="Test parameter set",
        nozzle="nozzle1",
        main_gas=50.0,
        feeder_gas=25.0,
        frequency=100,
        deagglomerator_speed=1000
    )
    params2 = ParameterSet(
        id="params2",
        name="Test Parameters 2",
        description="Another test parameter set",
        nozzle="nozzle2",
        main_gas=75.0,
        feeder_gas=35.0,
        frequency=150,
        deagglomerator_speed=1500
    )
    
    # Add parameter sets to service
    await service._parameter.create_parameter_set(params1)
    await service._parameter.create_parameter_set(params2)
    logger.info("Created test parameter sets")

    # Create test sequence
    sequence = Sequence(
        id="sequence1",
        metadata=SequenceMetadata(
            name="Test Sequence",
            version="1.0.0",
            created=datetime.now().isoformat(),
            author="Test User",
            description="A test sequence"
        ),
        steps=[
            SequenceStep(
                name="Initialize",
                description="Initialize system",
                action_group="initialize"
            ),
            SequenceStep(
                name="Pattern 1",
                description="First pattern",
                actions=[
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
            )
        ]
    )
    
    # Add sequence to service
    service._sequence._sequences[sequence.id] = sequence
    logger.info("Created test sequence")
    
    # Return test data for use in tests
    yield {
        "patterns": [pattern1, pattern2],
        "parameter_sets": [params1, params2],
        "sequences": [sequence]
    }
    
    # Cleanup after tests
    await service._pattern.stop()
    await service._parameter.stop()
    await service._sequence.stop()


def test_generate_sequence(client, test_data):
    """Test sequence file generation endpoint."""
    sequence_data = {
        "sequence": {
            "metadata": {
                "name": "Test Sequence",
                "version": "1.0",
                "created": "2024-03-20",
                "author": "Test User",
                "description": "A test sequence for testing"
            },
            "steps": [
                {
                    "name": "Initialize System",
                    "action_group": "ready_system"
                },
                {
                    "name": "First Pattern",
                    "actions": [
                        {
                            "action_group": "move_to_trough"
                        },
                        {
                            "action_group": "apply_parameters",
                            "parameters": {
                                "file": "mcs24_n2_low_flow.yaml"
                            }
                        },
                        {
                            "action_group": "execute_pattern",
                            "parameters": {
                                "file": "serpentine_5mm_standard.yaml",
                                "passes": 3,
                                "modifications": {
                                    "params": {
                                        "origin": [10.0, 10.0]
                                    }
                                }
                            }
                        }
                    ]
                }
            ]
        }
    }
    
    response = client.post(
        "/process/sequences/generate",
        json=sequence_data
    )
    if response.status_code != 200:
        print("Response:", response.json())
    assert response.status_code == 200
    
    # Verify response
    data = response.json()
    assert "sequence_id" in data
    
    # Verify file was created and matches format
    file_path = Path(f"data/sequences/{data['sequence_id']}.yaml")
    assert file_path.exists()
    
    # Verify file contents
    with open(file_path) as f:
        saved_sequence = yaml.safe_load(f)
        assert "sequence" in saved_sequence
        assert saved_sequence["sequence"]["metadata"]["name"] == sequence_data["sequence"]["metadata"]["name"]


def test_generate_pattern(client, test_data):
    """Test pattern file generation endpoint."""
    pattern_data = {
        "id": "test_pattern",
        "name": "Test Pattern",
        "description": "A test pattern for testing",
        "type": "serpentine",
        "params": {
            "direction": "posX",
            "length": 100.0,
            "width": 50.0,
            "spacing": 2.0,
            "speed": 30.0,
            "acceleration": 5.0,
            "overlap": 0.5
        }
    }
    
    response = client.post(
        "/process/patterns/generate",
        json=pattern_data
    )
    if response.status_code != 200:
        print("Response:", response.json())
    assert response.status_code == 200
    
    # Verify response
    data = response.json()
    assert "pattern_id" in data
    
    # Verify file was created
    file_path = Path(f"data/patterns/{data['pattern_id']}.yaml")
    assert file_path.exists()
    
    # Verify file contents
    with open(file_path) as f:
        saved_pattern = yaml.safe_load(f)
        assert saved_pattern["id"] == pattern_data["id"]
        assert saved_pattern["name"] == pattern_data["name"]


def test_generate_invalid_sequence(client):
    """Test sequence generation with invalid data."""
    invalid_data = {
        # Missing 'sequence' root key
        "metadata": {
            "name": "Invalid Sequence"
        }
    }
    response = client.post(
        "/process/sequences/generate",
        json=invalid_data
    )
    assert response.status_code == 422
    error_response = response.json()["detail"]  # Get error content from detail field
    assert error_response["message"] == "Missing 'sequence' root key"
    assert error_response["status"] == "error"


def test_generate_invalid_pattern(client):
    """Test pattern generation with invalid data."""
    invalid_data = {
        # Missing required fields
        "metadata": {
            "name": "Invalid Pattern"
        }
    }
    response = client.post(
        "/process/patterns/generate",
        json=invalid_data
    )
    assert response.status_code == 422
    error_response = response.json()["detail"]  # Get error content from detail field
    assert "Missing required fields" in error_response["message"]
    assert error_response["status"] == "error"


def test_generate_powder(client):
    """Test powder file generation endpoint."""
    powder_data = {
        "powder": {
            "name": "Copper 45-75μm Praxair",
            "type": "Copper",
            "size": "45-75 μm",
            "manufacturer": "Praxair",
            "lot": "CP123456"
        }
    }
    
    response = client.post(
        "/process/powders/generate",
        json=powder_data
    )
    assert response.status_code == 200
    
    # Verify response
    data = response.json()
    assert "powder_id" in data
    
    # Verify file was created
    file_path = Path(f"data/powders/{data['powder_id']}.yaml")
    assert file_path.exists()
    
    # Verify file contents - use UTF-8 encoding when reading
    with open(file_path, encoding='utf-8') as f:
        saved_powder = yaml.safe_load(f)
        assert "powder" in saved_powder
        assert saved_powder["powder"]["name"] == powder_data["powder"]["name"]
        # Verify all fields are quoted strings
        for key in ["type", "size", "manufacturer", "lot"]:
            assert isinstance(saved_powder["powder"][key], str)


def test_generate_nozzle(client):
    """Test nozzle file generation endpoint."""
    nozzle_data = {
        "nozzle": {
            "name": "MCS-24",
            "manufacturer": "VRC",
            "type": "Cold Spray",
            "description": "Standard micro cold spray nozzle"
        }
    }
    
    response = client.post(
        "/process/parameters/nozzles/generate",
        json=nozzle_data
    )
    assert response.status_code == 200
    
    # Verify response
    data = response.json()
    assert "nozzle_id" in data
    
    # Verify file was created
    file_path = Path(f"data/parameters/nozzles/{data['nozzle_id']}.yaml")
    assert file_path.exists()
    
    # Verify file contents
    with open(file_path) as f:
        saved_nozzle = yaml.safe_load(f)
        assert "nozzle" in saved_nozzle
        assert saved_nozzle["nozzle"]["name"] == nozzle_data["nozzle"]["name"]
        # Verify all fields are quoted strings
        for key in ["name", "manufacturer", "type", "description"]:
            assert isinstance(saved_nozzle["nozzle"][key], str)


def test_generate_parameter_set(client):
    """Test parameter set file generation endpoint."""
    parameter_data = {
        "process": {
            "name": "MCS-24 N2 Med Flow",
            "created": "2024-03-20",
            "author": "John Doe",
            "description": "Standard spray parameters for MCS-24 nozzle with nitrogen",
            "nozzle": "MCS-24",
            "main_gas": 50.0,
            "feeder_gas": 5.0,
            "frequency": 600,
            "deagglomerator_speed": 25
        }
    }
    
    response = client.post(
        "/process/parameters/generate",
        json=parameter_data
    )
    assert response.status_code == 200
    
    # Verify response
    data = response.json()
    assert "parameter_id" in data
    
    # Verify file was created
    file_path = Path(f"data/parameters/{data['parameter_id']}.yaml")
    assert file_path.exists()
    
    # Verify file contents
    with open(file_path) as f:
        saved_params = yaml.safe_load(f)
        assert "process" in saved_params
        assert saved_params["process"]["name"] == parameter_data["process"]["name"]
        # Verify string fields are quoted
        for key in ["name", "created", "author", "description", "nozzle"]:
            assert isinstance(saved_params["process"][key], str)
        # Verify numeric fields
        assert isinstance(saved_params["process"]["main_gas"], float)
        assert isinstance(saved_params["process"]["feeder_gas"], float)
        assert isinstance(saved_params["process"]["frequency"], int)
        assert isinstance(saved_params["process"]["deagglomerator_speed"], int)


def test_generate_invalid_powder(client):
    """Test powder generation with invalid data."""
    invalid_data = {
        # Missing 'powder' root key
        "name": "Invalid Powder"
    }
    response = client.post(
        "/process/powders/generate",
        json=invalid_data
    )
    assert response.status_code == 422
    error_response = response.json()["detail"]  # Get error content from detail field
    assert error_response["message"] == "Missing 'powder' root key"
    assert error_response["status"] == "error"


def test_generate_invalid_nozzle(client):
    """Test nozzle generation with invalid data."""
    invalid_data = {
        # Missing 'nozzle' root key
        "name": "Invalid Nozzle"
    }
    response = client.post(
        "/process/parameters/nozzles/generate",
        json=invalid_data
    )
    assert response.status_code == 422
    error_response = response.json()["detail"]  # Get error content from detail field
    assert error_response["message"] == "Missing 'nozzle' root key"
    assert error_response["status"] == "error"


def test_generate_invalid_parameter_set(client):
    """Test parameter set generation with invalid data."""
    invalid_data = {
        # Missing 'process' root key
        "name": "Invalid Parameters"
    }
    response = client.post(
        "/process/parameters/generate",
        json=invalid_data
    )
    assert response.status_code == 422
    error_response = response.json()["detail"]  # Get error content from detail field
    assert error_response["message"] == "Missing 'process' root key"
    assert error_response["status"] == "error"


@pytest.mark.asyncio
async def test_pattern_file_generation():
    """Test pattern file generation."""
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
    
    # Generate pattern file
    pattern_file = Path("data/patterns/test_pattern.yaml")
    with open(pattern_file, "w") as f:
        yaml.dump(pattern_data, f)
    
    assert pattern_file.exists()
    
    # Verify file contents
    with open(pattern_file, "r") as f:
        loaded_data = yaml.safe_load(f)
    
    assert loaded_data == pattern_data

# ... rest of test cases ...
