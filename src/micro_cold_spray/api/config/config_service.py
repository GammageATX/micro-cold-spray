"""Configuration service implementation."""

import os
from typing import Dict, Any
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from micro_cold_spray.api.base.base_errors import create_error
from micro_cold_spray.api.config.services import (
    CacheService,
    FileService,
    FormatService,
    RegistryService,
    SchemaService
)
from micro_cold_spray.api.config.endpoints import get_config_router


# Default paths
DEFAULT_CONFIG_PATH = os.path.join(os.getcwd(), "config")
DEFAULT_SCHEMA_PATH = os.path.join(DEFAULT_CONFIG_PATH, "schemas")


async def load_configurations(app: FastAPI):
    """Load all configurations from disk and warm up cache.
    
    Args:
        app: FastAPI application instance
    """
    try:
        # Get list of config files
        config_files = app.state.file.list_configs()
        logger.info(f"Found {len(config_files)} configuration files")

        # Load each config
        for filename in config_files:
            try:
                # Extract config name from filename
                name = os.path.splitext(filename)[0]
                
                # Read config from file
                logger.debug(f"Loading configuration: {name}")
                raw_data = app.state.file.read(filename)
                
                # Parse YAML content
                config_data = app.state.format.parse(raw_data, "yaml")
                
                # Register in registry
                app.state.registry.register(name, config_data)
                
                # Cache the config
                app.state.cache.set(name, config_data)
                
                logger.info(f"Loaded and cached configuration: {name}")
                
            except Exception as e:
                logger.error(f"Failed to load configuration {filename}: {e}")
                continue

        # Load schemas if they exist
        schema_dir = os.path.join(app.state.file.base_path, "schemas")
        if os.path.exists(schema_dir):
            schema_files = [f for f in os.listdir(schema_dir) if f.endswith('.json')]
            logger.info(f"Found {len(schema_files)} schema files")
            
            for filename in schema_files:
                try:
                    # Extract schema name
                    name = os.path.splitext(filename)[0]
                    
                    # Read schema
                    logger.debug(f"Loading schema: {name}")
                    with open(os.path.join(schema_dir, filename), 'r') as f:
                        schema_data = app.state.format.parse(f.read(), "json")
                    
                    # Register schema
                    app.state.schema.register_schema(name, schema_data)
                    logger.info(f"Loaded schema: {name}")
                    
                except Exception as e:
                    logger.error(f"Failed to load schema {filename}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Failed to load configurations: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to load configurations: {str(e)}"
        )


def create_config_service() -> FastAPI:
    """Create configuration service.
    
    Returns:
        FastAPI: Application instance
    """
    app = FastAPI(title="Configuration Service")
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["*"],
    )
    
    # Get config path from environment or use default
    config_path = os.getenv("CONFIG_SERVICE_PATH", DEFAULT_CONFIG_PATH)
    logger.info(f"Using config path: {config_path}")
    
    # Initialize services
    app.state.file = FileService(base_path=config_path)
    app.state.cache = CacheService()
    app.state.format = FormatService()
    app.state.registry = RegistryService()
    app.state.schema = SchemaService()
    
    @app.on_event("startup")
    async def startup():
        """Start services and load configurations."""
        try:
            # Start services
            logger.info("Starting services...")
            await app.state.file.start()
            await app.state.cache.start()
            await app.state.format.start()
            await app.state.registry.start()
            await app.state.schema.start()
            logger.info("All services started successfully")
            
            # Load configurations
            await load_configurations(app)
            
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to start config service: {str(e)}"
            )
    
    @app.on_event("shutdown")
    async def shutdown():
        """Stop all services."""
        try:
            logger.info("Stopping services...")
            await app.state.schema.stop()
            await app.state.registry.stop()
            await app.state.format.stop()
            await app.state.cache.stop()
            await app.state.file.stop()
            logger.info("All services stopped successfully")
            
        except Exception as e:
            logger.error(f"Shutdown failed: {e}")
            raise create_error(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                message=f"Failed to stop config service: {str(e)}"
            )
    
    # Include config router
    app.include_router(get_config_router())
    
    return app
