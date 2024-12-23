"""Service UI router."""

from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import FastAPI, Request, WebSocket, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import asyncio
import aiohttp

from micro_cold_spray.api.base.base_errors import create_error
from .utils import get_uptime, get_memory_usage, monitor_service_logs


class ApiUrls(BaseModel):
    """API URLs configuration model."""
    config: str = Field("http://localhost:8001", description="Config service URL")
    messaging: str = Field("http://localhost:8002", description="Messaging service URL")
    communication: str = Field("http://localhost:8003", description="Communication service URL")
    state: str = Field("http://localhost:8004", description="State service URL")
    process: str = Field("http://localhost:8005", description="Process service URL")
    data_collection: str = Field("http://localhost:8006", description="Data collection service URL")
    validation: str = Field("http://localhost:8007", description="Validation service URL")
    ws: Dict[str, str] = Field(
        default_factory=lambda: {
            "messaging": "ws://localhost:8002/messaging/subscribe",
            "state": "ws://localhost:8004/state/monitor",
            "tags": "ws://localhost:8003/communication/tags",
            "services": "ws://localhost:8000/monitoring/logs"
        },
        description="WebSocket endpoints"
    )


class ServiceInfo(BaseModel):
    """Service information model."""
    running: bool = Field(..., description="Service running status")
    version: str = Field("1.0.0", description="Service version")
    error: Optional[str] = Field(None, description="Error message if any")


class ServiceStatus(BaseModel):
    """Service status model."""
    name: str = Field(..., description="Service name")
    port: int = Field(..., description="Service port")
    status: str = Field(..., description="Service status")
    uptime: float = Field(..., description="Service uptime in seconds")
    memory_usage: Dict[str, float] = Field(..., description="Memory usage stats")
    service_info: ServiceInfo = Field(..., description="Detailed service info")


class ServiceControlResponse(BaseModel):
    """Service control response model."""
    status: str = Field(..., description="Operation status")
    message: str = Field(..., description="Response message")


class LogMessage(BaseModel):
    """Log message model."""
    timestamp: datetime = Field(..., description="Message timestamp")
    service: str = Field(..., description="Source service")
    level: str = Field(..., description="Log level")
    message: str = Field(..., description="Log message")


def get_api_urls() -> ApiUrls:
    """Get API URLs for templates."""
    return ApiUrls()


async def check_service_health(url: str) -> ServiceInfo:
    """Check service health status.
    
    Args:
        url: Service base URL
        
    Returns:
        ServiceInfo with status details
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{url}/health", timeout=2) as response:
                if response.status == 200:
                    data = await response.json()
                    return ServiceInfo(
                        running=True,
                        version=data.get("version", "1.0.0"),
                        error=None
                    )
                return ServiceInfo(
                    running=False,
                    error=f"Service returned status {response.status}"
                )
    except Exception as e:
        return ServiceInfo(
            running=False,
            error=str(e)
        )


def create_app() -> FastAPI:
    """Create FastAPI application."""
    try:
        app = FastAPI(
            title="MicroColdSpray UI",
            description="Web interface for MicroColdSpray system",
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

        # Mount static files
        app.mount(
            "/static",
            StaticFiles(directory=Path(__file__).parent / "static"),
            name="static"
        )

        # Setup templates
        templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

        @app.get(
            "/",
            response_class=HTMLResponse,
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def index(request: Request) -> HTMLResponse:
            """Render index page."""
            try:
                return templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "api_urls": get_api_urls().dict()
                    }
                )
            except Exception as e:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to render index page",
                    context={"error": str(e)},
                    cause=e
                )

        @app.get(
            "/health",
            response_model=Dict[str, str],
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def health() -> Dict[str, str]:
            """Health check endpoint."""
            try:
                return {
                    "status": "ok",
                    "uptime": str(get_uptime()),
                    "memory": str(get_memory_usage())
                }
            except Exception as e:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Health check failed",
                    context={"error": str(e)},
                    cause=e
                )

        @app.get(
            "/monitoring/services",
            response_class=HTMLResponse,
            responses={
                status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
            }
        )
        async def services_monitor(request: Request) -> HTMLResponse:
            """Render services monitor page."""
            try:
                return templates.TemplateResponse(
                    "monitoring/services.html",
                    {
                        "request": request,
                        "api_urls": get_api_urls().dict()
                    }
                )
            except Exception as e:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to render services monitor page",
                    context={"error": str(e)},
                    cause=e
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
                    "config": api_urls.config,
                    "communication": api_urls.communication,
                    "messaging": api_urls.messaging,
                    "state": api_urls.state,
                    "data_collection": api_urls.data_collection,
                    "validation": api_urls.validation
                }.items():
                    service_info = await check_service_health(url)
                    port = int(url.split(":")[-1])
                    
                    services[service_name] = ServiceStatus(
                        name=service_name,
                        port=port,
                        status="ok" if service_info.running else "error",
                        uptime=get_uptime(),
                        memory_usage=get_memory_usage(),
                        service_info=service_info
                    )

                return services
            except Exception as e:
                raise create_error(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    message="Failed to get services status",
                    context={"error": str(e)},
                    cause=e
                )

        @app.websocket("/monitoring/logs")
        async def service_logs(websocket: WebSocket):
            """WebSocket endpoint for service logs."""
            await websocket.accept()
            try:
                while True:
                    # Monitor logs every second
                    log_entry = await monitor_service_logs()
                    if log_entry:
                        await websocket.send_json(log_entry)
                    await asyncio.sleep(1)
            except Exception:
                await websocket.close()

        return app

    except Exception as e:
        raise create_error(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            message="Failed to create UI application",
            context={"error": str(e)},
            cause=e
        )


# Create FastAPI application instance
app = create_app()
