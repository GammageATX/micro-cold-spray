"""Service UI router."""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from loguru import logger
import aiohttp

from micro_cold_spray.utils.errors import create_error
from micro_cold_spray.utils.health import get_uptime, ServiceHealth, ComponentHealth


class ApiUrls(BaseModel):
    """API URLs configuration model."""
    ui: str = Field("http://localhost:8000", description="UI service URL")
    config: str = Field("http://localhost:8001", description="Config service URL")
    state: str = Field("http://localhost:8002", description="State service URL")
    communication: str = Field("http://localhost:8003", description="Communication service URL")
    process: str = Field("http://localhost:8004", description="Process service URL")
    data_collection: str = Field("http://localhost:8005", description="Data collection service URL")
    validation: str = Field("http://localhost:8006", description="Validation service URL")


class ServiceStatus(BaseModel):
    """Service status model."""
    name: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    status: str = Field(..., description="Service status")
    uptime: float = Field(..., description="Service uptime in seconds")
    version: str = Field(..., description="Service version")
    mode: Optional[str] = Field(None, description="Service mode")
    error: Optional[str] = Field(None, description="Error message if any")
    components: Optional[Dict[str, ComponentHealth]] = Field(None, description="Component health statuses")


def get_api_urls() -> ApiUrls:
    """Get API URLs for templates."""
    return ApiUrls()


async def check_service_health(url: str, service_name: str = None) -> ServiceHealth:
    """Check service health status.
    
    Args:
        url: Service base URL
        service_name: Name of the service (optional)
        
    Returns:
        ServiceHealth with status details
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health", timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    return ServiceHealth(**data)
                return ServiceHealth(
                    status="error",
                    service=service_name or "unknown",
                    version="1.0.0",
                    is_running=False,
                    uptime=0.0,
                    error=f"Service returned status {response.status}"
                )
    except Exception as e:
        return ServiceHealth(
            status="error",
            service=service_name or "unknown",
            version="1.0.0",
            is_running=False,
            uptime=0.0,
            error=str(e)
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    try:
        app = FastAPI(
            title="MicroColdSpray Service Monitor",
            description="Service monitoring interface for MicroColdSpray system",
            version="1.0.0"
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Add GZip middleware
        app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Setup templates and static files
        templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
        static_dir = Path(__file__).parent / "static"
        if static_dir.exists():
            from fastapi.staticfiles import StaticFiles
            app.mount("/static", StaticFiles(directory=static_dir), name="static")

        @app.get(
            "/",
            response_class=HTMLResponse,
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def index(request: Request) -> HTMLResponse:
            """Render service monitor page."""
            try:
                return templates.TemplateResponse(
                    "monitoring/services.html",
                    {
                        "request": request,
                        "api_urls": get_api_urls().dict()
                    }
                )
            except Exception as e:
                logger.error(f"Failed to render service monitor page: {e}")
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Failed to render service monitor page: {str(e)}"
                )

        @app.get(
            "/health",
            response_model=ServiceHealth,
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def health() -> ServiceHealth:
            """Health check endpoint."""
            try:
                return ServiceHealth(
                    status="ok",
                    service="ui",
                    version=app.version,
                    is_running=True,
                    uptime=get_uptime(),
                    error=None,
                    timestamp=datetime.now()
                )
            except Exception as e:
                error_msg = f"Health check failed: {str(e)}"
                logger.error(error_msg)
                return ServiceHealth(
                    status="error",
                    service="ui",
                    version=app.version,
                    is_running=False,
                    uptime=0.0,
                    error=error_msg,
                    timestamp=datetime.now()
                )

        @app.get(
            "/monitoring/services/status",
            response_model=Dict[str, ServiceStatus],
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def get_services_status() -> Dict[str, ServiceStatus]:
            """Get status of all services."""
            services: Dict[str, ServiceStatus] = {}
            api_urls = get_api_urls()
            
            try:
                for service_name, url in {
                    "ui": api_urls.ui,
                    "config": api_urls.config,
                    "state": api_urls.state,
                    "communication": api_urls.communication,
                    "process": api_urls.process,
                    "data_collection": api_urls.data_collection,
                    "validation": api_urls.validation
                }.items():
                    health = await check_service_health(url, service_name)
                    port = int(url.split(":")[-1])
                    
                    # Convert component health dictionaries to ComponentHealth objects
                    components = None
                    if health.components:
                        components = {
                            name: ComponentHealth(
                                status=comp.get("status", "error"),
                                error=comp.get("error")
                            ) if isinstance(comp, dict) else comp
                            for name, comp in health.components.items()
                        }
                    
                    services[service_name] = ServiceStatus(
                        name=service_name,
                        port=port,
                        status=health.status,
                        uptime=health.uptime,
                        version=health.version,
                        mode=health.mode,
                        error=health.error,
                        components=components
                    )

                return services
            except Exception as e:
                logger.error(f"Failed to get services status: {e}")
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message=f"Failed to get services status: {str(e)}"
                )

        return app

    except Exception as e:
        logger.error(f"Failed to create UI application: {e}")
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message=f"Failed to create UI application: {str(e)}"
        )
