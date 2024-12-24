"""Process API main script for testing."""

import asyncio
import uvicorn
from datetime import datetime
from loguru import logger
from fastapi import FastAPI

from micro_cold_spray.api.process.process_app import create_app
from micro_cold_spray.api.process.models.process_models import (
    ProcessPattern,
    ParameterSet,
    SequenceStep,
    SequenceMetadata
)
from micro_cold_spray.api.process.process_service import ProcessService


async def create_test_data(service: ProcessService) -> None:
    """Create test data for process service.
    
    Args:
        service: Process service instance
    """
    # Create test patterns
    pattern1 = ProcessPattern(
        id="pattern1",
        name="Test Pattern 1",
        description="A test pattern for testing",
        parameters={
            "speed": 100,
            "temperature": 200,
            "pressure": 300
        }
    )
    pattern2 = ProcessPattern(
        id="pattern2",
        name="Test Pattern 2",
        description="Another test pattern",
        parameters={
            "speed": 150,
            "temperature": 250,
            "pressure": 350
        }
    )
    await service._pattern.create_pattern(pattern1)
    await service._pattern.create_pattern(pattern2)
    logger.info("Created test patterns")

    # Create test parameter sets
    params1 = ParameterSet(
        id="params1",
        name="Test Parameters 1",
        description="Test parameter set for testing",
        parameters={
            "speed": 120,
            "temperature": 220,
            "pressure": 320
        }
    )
    params2 = ParameterSet(
        id="params2",
        name="Test Parameters 2",
        description="Another test parameter set",
        parameters={
            "speed": 170,
            "temperature": 270,
            "pressure": 370
        }
    )
    await service._parameter.create_parameter_set(params1)
    await service._parameter.create_parameter_set(params2)
    logger.info("Created test parameter sets")

    # Create test sequence
    sequence = SequenceMetadata(
        id="sequence1",
        name="Test Sequence",
        description="A test sequence for testing",
        steps=[
            SequenceStep(
                id="step1",
                name="Step 1",
                description="First test step",
                pattern_id=pattern1.id,
                parameter_set_id=params1.id,
                order=1
            ),
            SequenceStep(
                id="step2",
                name="Step 2",
                description="Second test step",
                pattern_id=pattern2.id,
                parameter_set_id=params2.id,
                order=2
            )
        ]
    )
    # Add sequence directly to the service's sequence dictionary
    service._sequence._sequences[sequence.id] = sequence
    logger.info("Created test sequence")


async def init_service() -> ProcessService:
    """Initialize process service with test data.
    
    Returns:
        Initialized process service
    """
    service = ProcessService()
    await service.initialize()
    await service.start()
    logger.info("Process service started")

    await create_test_data(service)
    logger.info("Test data created")

    return service


def create_test_app() -> FastAPI:
    """Create FastAPI application with test data.
    
    Returns:
        FastAPI application
    """
    # Initialize service with test data
    service = asyncio.run(init_service())

    # Create FastAPI app
    app = create_app()

    # Store service in app state
    app.state.process_service = service

    return app


def main():
    """Main function for testing process service."""
    # Create FastAPI app with test data
    app = create_test_app()

    # Configure uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8004,
        log_level="info"
    )


if __name__ == "__main__":
    main()
