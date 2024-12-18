"""Service UI router."""

from pathlib import Path
from datetime import datetime
from typing import Dict, List
from fastapi import FastAPI, Request, WebSocket, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
import asyncio

from .utils import get_uptime, get_memory_usage


class ApiUrls(BaseModel):
    """API URLs configuration model."""
    config: str
    communication: str
    messaging: str
    state: str
    data_collection: str
    ws: Dict[str, str]


class TestScenario(BaseModel):
    """Test scenario model."""
    name: str
    description: str
    steps: List[str]


class TestScenarios(BaseModel):
    """Test scenarios collection model."""
    motion: TestScenario
    gas: TestScenario


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    uptime: float
    memory: Dict[str, float]


class ServiceInfo(BaseModel):
    """Service information model."""
    running: bool
    version: str = "1.0.0"
    error: str = ""


class ServiceStatus(BaseModel):
    """Service status model."""
    name: str
    port: int
    status: str
    uptime: float
    memory_usage: Dict[str, float]
    service_info: ServiceInfo


class ServiceControlResponse(BaseModel):
    """Service control response model."""
    status: str
    message: str


class LogMessage(BaseModel):
    """Log message model."""
    timestamp: datetime
    service: str
    level: str
    message: str


app = FastAPI(title="MicroColdSpray UI")

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def get_api_urls() -> ApiUrls:
    """Get API URLs for templates."""
    return ApiUrls(
        config="http://localhost:8001",
        communication="http://localhost:8002",
        messaging="http://localhost:8007",
        state="http://localhost:8004",
        data_collection="http://localhost:8005",
        ws={
            "messaging": "ws://localhost:8007/messaging/subscribe",
            "state": "ws://localhost:8004/state/monitor",
            "tags": "ws://localhost:8002/communication/tags",
            "services": "ws://localhost:8000/monitoring/logs"
        }
    )


def get_test_scenarios() -> TestScenarios:
    """Get available test scenarios."""
    return TestScenarios(
        motion=TestScenario(
            name="Motion System Test",
            description="Test motion control system",
            steps=["home", "move_x", "move_y", "move_z"]
        ),
        gas=TestScenario(
            name="Gas Control Test",
            description="Test gas control system",
            steps=["valve_open", "set_flow", "valve_close"]
        )
    )


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
                "api_urls": get_api_urls().dict(),
                "test_scenarios": get_test_scenarios().dict()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/health",
    response_model=HealthResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
async def health() -> HealthResponse:
    """Health check endpoint."""
    try:
        return HealthResponse(
            status="ok",
            uptime=get_uptime(),
            memory=get_memory_usage()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/testing",
    response_class=HTMLResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
async def testing_interface(request: Request) -> HTMLResponse:
    """Render testing interface."""
    try:
        return templates.TemplateResponse(
            "testing/index.html",
            {
                "request": request,
                "api_urls": get_api_urls().dict(),
                "test_scenarios": get_test_scenarios().dict()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get(
    "/testing/tags",
    response_class=HTMLResponse,
    responses={
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
async def tag_monitor(request: Request) -> HTMLResponse:
    """Render tag monitor interface."""
    try:
        return templates.TemplateResponse(
            "testing/tag_monitor.html",
            {
                "request": request,
                "api_urls": get_api_urls().dict()
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
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
    base_services = {
        "config": {"port": 8001},
        "communication": {"port": 8002},
        "messaging": {"port": 8007},
        "state": {"port": 8004},
        "data_collection": {"port": 8005}
    }

    try:
        for service_name, service_info in base_services.items():
            try:
                services[service_name] = ServiceStatus(
                    name=service_name,
                    port=service_info["port"],
                    status="ok",
                    uptime=get_uptime(),
                    memory_usage=get_memory_usage(),
                    service_info=ServiceInfo(
                        running=True,
                        version="1.0.0"
                    )
                )
            except Exception as e:
                services[service_name] = ServiceStatus(
                    name=service_name,
                    port=service_info["port"],
                    status="error",
                    uptime=0.0,
                    memory_usage={"total": 0.0, "used": 0.0},
                    service_info=ServiceInfo(
                        running=False,
                        error=str(e)
                    )
                )

        return services
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post(
    "/monitoring/services/control",
    response_model=ServiceControlResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid service or action"},
        status.HTTP_500_INTERNAL_SERVER_ERROR: {"description": "Internal server error"}
    }
)
async def control_service(service: str, action: str) -> ServiceControlResponse:
    """Control a service (start/stop/restart)."""
    valid_services = {"config", "communication", "messaging", "state", "data_collection"}
    valid_actions = {"start", "stop", "restart"}

    try:
        if service not in valid_services:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service: {service}"
            )
        if action not in valid_actions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}"
            )

        # Implement service control logic here
        return ServiceControlResponse(
            status="success",
            message=f"{action} {service} successful"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.websocket("/monitoring/logs")
async def service_logs(websocket: WebSocket):
    """WebSocket endpoint for service logs."""
    await websocket.accept()
    try:
        while True:
            # Send log updates every second
            await asyncio.sleep(1)
            log_message = LogMessage(
                timestamp=datetime.now(),
                service="system",
                level="INFO",
                message="System running normally"
            )
            await websocket.send_json(log_message.dict())
    except Exception:
        await websocket.close()
