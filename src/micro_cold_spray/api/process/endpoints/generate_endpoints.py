"""Generate endpoints for process API."""

from typing import Dict, Any
from pathlib import Path
from datetime import datetime
import yaml
from fastapi import Depends, status, HTTPException
from loguru import logger

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.api.process.process_service import ProcessService
from micro_cold_spray.api.process.endpoints.dependencies import get_service
from micro_cold_spray.api.process.validators.parameter_validator import validate_parameter


async def generate_sequence(sequence_data: Dict[str, Any], service: ProcessService = Depends(get_service)) -> Dict[str, str]:
    """Generate sequence file."""
    # Validate first
    if "sequence" not in sequence_data:
        logger.error("Missing 'sequence' root key")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Missing 'sequence' root key"
        )
    
    try:
        sequence = sequence_data["sequence"]
        metadata = sequence["metadata"]
        
        # Generate descriptive ID
        name = metadata["name"]
        author = metadata["author"]
        version = metadata["version"]
        timestamp = datetime.now().strftime("%Y%m%d")
        sequence_id = f"{name}-{author}-v{version}-{timestamp}"
        sequence_id = sequence_id.lower().replace(" ", "_")
        
        sequence_path = Path(f"data/sequences/{sequence_id}.yaml")
        sequence_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(sequence_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                sequence_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
                allow_unicode=True
            )
        return {"sequence_id": sequence_id}
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_msg = f"Failed to generate sequence: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
        raise


async def generate_pattern(pattern_data: Dict[str, Any], service: ProcessService = Depends(get_service)) -> Dict[str, str]:
    """Generate pattern file."""
    # Validate first
    required_fields = ["id", "name", "description", "type", "params"]
    missing = [field for field in required_fields if field not in pattern_data]
    if missing:
        error_msg = f"Missing required fields: {', '.join(missing)}"
        logger.error(error_msg)
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=error_msg
        )

    try:
        # Generate descriptive ID from pattern properties
        pattern_type = pattern_data["type"]
        params = pattern_data["params"]
        direction = params.get("direction", "default")
        length = str(int(params.get("length", 0)))
        width = str(int(params.get("width", 0)))
        
        pattern_id = f"{pattern_type}-{length}x{width}-{direction}"
        pattern_id = pattern_id.lower().replace(" ", "_")
        
        pattern_path = Path(f"data/patterns/{pattern_id}.yaml")
        pattern_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(pattern_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                pattern_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
                allow_unicode=True
            )
            
        return {"pattern_id": pattern_id}
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_msg = f"Failed to generate pattern: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
        raise


async def generate_powder(powder_data: Dict[str, Any], service: ProcessService = Depends(get_service)) -> Dict[str, str]:
    """Generate powder file."""
    # Validate first
    if "powder" not in powder_data:
        logger.error("Missing 'powder' root key")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Missing 'powder' root key"
        )
    
    try:
        powder = powder_data["powder"]
        required_fields = ["name", "type", "size", "manufacturer", "lot"]
        missing = [field for field in required_fields if field not in powder]
        if missing:
            error_msg = f"Missing required powder fields: {', '.join(missing)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=error_msg
            )
        
        # Generate ID from name if not provided
        size_range = powder["size"].replace(" ", "")  # e.g. "45-75μm"
        powder_id = f"{powder['type']}-{size_range}-{powder['manufacturer']}-{powder['lot']}"
        powder_id = powder_id.lower().replace(" ", "_")
        powder_path = Path(f"data/powders/{powder_id}.yaml")
        powder_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(powder_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                powder_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
                allow_unicode=True
            )
            
        return {"powder_id": powder_id}
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_msg = f"Failed to generate powder: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
        raise


async def generate_nozzle(nozzle_data: Dict[str, Any], service: ProcessService = Depends(get_service)) -> Dict[str, str]:
    """Generate nozzle file."""
    # Validate first
    if "nozzle" not in nozzle_data:
        logger.error("Missing 'nozzle' root key")
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message="Missing 'nozzle' root key"
        )
    try:
        nozzle = nozzle_data["nozzle"]
        required_fields = ["name", "manufacturer", "type", "description"]
        missing = [field for field in required_fields if field not in nozzle]
        if missing:
            error_msg = f"Missing required nozzle fields: {', '.join(missing)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=error_msg
            )
        
        # Generate ID from name if not provided
        nozzle_id = f"{nozzle['type']}-{nozzle['name']}-{nozzle['manufacturer']}"
        nozzle_id = nozzle_id.lower().replace(" ", "_")
        nozzle_path = Path(f"data/nozzles/{nozzle_id}.yaml")
        nozzle_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(nozzle_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                nozzle_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
                allow_unicode=True
            )
            
        return {"nozzle_id": nozzle_id}
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_msg = f"Failed to generate nozzle: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
        raise


async def generate_parameter(parameter_data: Dict[str, Any], service: ProcessService = Depends(get_service)) -> Dict[str, str]:
    """Generate parameter file."""
    # Validate data
    is_valid, errors = validate_parameter(parameter_data)
    if not is_valid:
        raise create_error(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            message=f"Invalid parameter data: {errors}"
        )
    
    try:
        # Validate against schema first
        validation_response = await service._validation.validate_parameter(parameter_data)
        if not validation_response.valid:
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=f"Invalid parameter data: {validation_response.errors}"
            )

        process = parameter_data["process"]
        required_fields = ["name", "created", "author", "description", "nozzle",
                           "main_gas", "feeder_gas", "frequency", "deagglomerator_speed"]
        missing = [field for field in required_fields if field not in process]
        if missing:
            error_msg = f"Missing required process fields: {', '.join(missing)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                message=error_msg
            )
        
        param_id = process.get("id", process["name"].lower().replace(" ", "_"))
        param_path = Path(f"data/parameters/{param_id}.yaml")
        param_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(param_path, 'w', encoding='utf-8') as f:
            yaml.safe_dump(
                parameter_data,
                f,
                sort_keys=False,
                default_flow_style=False,
                width=1000,
                allow_unicode=True
            )
            
        return {"parameter_id": param_id}
        
    except Exception as e:
        if not isinstance(e, HTTPException):
            error_msg = f"Failed to generate parameter: {str(e)}"
            logger.error(error_msg)
            raise create_error(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                message=error_msg
            )
        raise
