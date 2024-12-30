"""Process API endpoints."""

from typing import List, Dict, Any
from fastapi import APIRouter, status, Depends, HTTPException
from loguru import logger
import json
from pathlib import Path
import yaml
import time
from datetime import datetime

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import ServiceHealth
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.models.process_models import (
    ExecutionStatus, ActionStatus, ProcessPattern, ParameterSet,
    SequenceMetadata, SequenceStep, Sequence, SequenceResponse,
    SequenceListResponse, PatternResponse, PatternListResponse,
    ParameterSetResponse, ParameterSetListResponse
)
from micro_cold_spray.api.process.endpoints.list_endpoints import (
    list_patterns, list_parameter_sets
)
from micro_cold_spray.api.process.endpoints.generate_endpoints import (
    generate_sequence, generate_pattern, generate_powder,
    generate_nozzle, generate_parameter_set
)
from micro_cold_spray.api.process.endpoints.dependencies import get_service


def create_process_router(process_service: ProcessService) -> APIRouter:
    """Create process router with endpoints."""
    process_router = APIRouter()
    
    # Add routes with extracted handlers
    process_router.add_api_route(
        "/patterns",
        list_patterns,
        methods=["GET"],
        response_model=PatternListResponse
    )
    process_router.add_api_route(
        "/parameters",
        list_parameter_sets,
        methods=["GET"],
        response_model=ParameterSetListResponse
    )
    process_router.add_api_route(
        "/sequences/generate",
        generate_sequence,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/patterns/generate",
        generate_pattern,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/powders/generate",
        generate_powder,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/parameters/nozzles/generate",
        generate_nozzle,
        methods=["POST"]
    )
    process_router.add_api_route(
        "/parameters/generate",
        generate_parameter_set,
        methods=["POST"]
    )
    
    return process_router
