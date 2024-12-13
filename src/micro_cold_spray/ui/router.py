"""Service UI router."""

from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import httpx
from loguru import logger
import asyncio

from .utils import get_uptime, get_memory_usage, monitor_service_logs

app = FastAPI(title="MicroColdSpray UI")

# Mount static files
app.mount(
    "/static",
    StaticFiles(directory=Path(__file__).parent / "static"),
    name="static"
)

# Setup templates
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# API base URLs
API_URLS = {
    "config": "http://localhost:8001",
    "communication": "http://localhost:8002",
    "messaging": "http://localhost:8007",
    # Comment out services that aren't ready yet
    # "process": "http://localhost:8003",
    "state": "http://localhost:8004",
    "data_collection": "http://localhost:8005",
    # "validation": "http://localhost:8006",
    "ws": {
        "messaging": "ws://localhost:8007/messaging/subscribe",
        "state": "ws://localhost:8004/state/monitor",
        "tags": "ws://localhost:8002/communication/tags",
        "services": "ws://localhost:8000/monitoring/logs"
    }
}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render home page."""
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


# Communication routes
@app.get("/communication/motion", response_class=HTMLResponse)
async def motion_control(request: Request):
    """Render motion control page."""
    return templates.TemplateResponse(
        "communication/motion.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/communication/equipment", response_class=HTMLResponse)
async def equipment_control(request: Request):
    """Render equipment control page."""
    return templates.TemplateResponse(
        "communication/equipment.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/communication/tags", response_class=HTMLResponse)
async def tag_monitor(request: Request):
    """Render tag monitor page."""
    return templates.TemplateResponse(
        "communication/tags.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


# Config routes
@app.get("/config/editor", response_class=HTMLResponse)
async def config_editor(request: Request):
    """Render config editor page."""
    return templates.TemplateResponse(
        "config/editor.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


# Process routes
@app.get("/process/parameters", response_class=HTMLResponse)
async def process_parameters(request: Request):
    """Render process parameters page."""
    return templates.TemplateResponse(
        "process/parameters.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/process/patterns", response_class=HTMLResponse)
async def pattern_editor(request: Request):
    """Render pattern editor page."""
    return templates.TemplateResponse(
        "process/patterns.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/process/sequences", response_class=HTMLResponse)
async def sequence_control(request: Request):
    """Render sequence control page."""
    return templates.TemplateResponse(
        "process/sequences.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


# State routes
@app.get("/state/monitor", response_class=HTMLResponse)
async def state_monitor(request: Request):
    """Render state monitor page."""
    return templates.TemplateResponse(
        "state/monitor.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/health")
async def health_check():
    """Check health of all services."""
    health = {}
    for service, url in API_URLS.items():
        if service != "ws":
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{url}/health")
                    health[service] = "ok" if response.status_code == 200 else "error"
            except Exception as e:
                health[service] = f"error: {str(e)}"
    return health


@app.get("/monitoring/services", response_class=HTMLResponse)
async def service_monitor(request: Request):
    """Render service monitoring page."""
    return templates.TemplateResponse(
        "monitoring/services.html",
        {
            "request": request,
            "api_urls": API_URLS,
            "ws_urls": API_URLS["ws"]
        }
    )


@app.get("/monitoring/services/status")
async def get_service_status():
    """Get status of all services."""
    services = {}
    
    async def check_service(name: str, url: str):
        """Check health of a single service."""
        error_msg = "Unknown error"  # Default error message
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{url}/health", timeout=2.0)
                if response.status_code == 200:
                    data = response.json()
                    logger.debug(f"Health check response for {name}: {data}")
                    return {
                        "name": name,
                        "status": data.get("status", "error"),
                        "running": data.get("service_info", {}).get("running", False),
                        "port": url.split(":")[-1],
                        "uptime": data.get("uptime", 0),
                        "memory_usage": data.get("memory_usage", 0),
                        "service_info": data.get("service_info", {}),
                        "error": data.get("error")
                    }
                else:
                    error_msg = f"Service returned status code: {response.status_code}"
                    logger.error(f"Failed health check for {name}: {error_msg}")
        except Exception as e:
            error_msg = str(e) if str(e) else type(e).__name__
            logger.error(f"Failed to check {name} service: {error_msg}")
        
        # If we get here, something went wrong
        return {
            "name": name,
            "status": "stopped",
            "running": False,
            "port": url.split(":")[-1],
            "uptime": 0,
            "memory_usage": 0,
            "service_info": {
                "name": name,
                "error": f"Service unreachable: {error_msg}"
            }
        }

    # Check all services in parallel
    tasks = []
    for service, url in API_URLS.items():
        if service != "ws":
            tasks.append(check_service(service, url))
    
    results = await asyncio.gather(*tasks)
    
    for result in results:
        services[result["name"]] = result
        
    return services


@app.post("/monitoring/services/control")
async def control_service(request: Request):
    """Control a service."""
    try:
        data = await request.json()
        service = data.get("service")
        action = data.get("action")
        
        if not service or not action:
            raise HTTPException(status_code=400, detail="Missing service or action")
            
        if service not in API_URLS or service == "ws":
            raise HTTPException(status_code=400, detail="Invalid service")
            
        try:
            # Send control signal to service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{API_URLS[service]}/control",
                    json={"action": action},
                    timeout=5.0  # Add timeout
                )
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Service returned error: {response.text}"
                    )
                return await response.json()
        except httpx.TimeoutError:
            raise HTTPException(
                status_code=504,
                detail=f"Timeout while controlling service: {service}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to control service: {str(e)}"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in control_service: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


@app.websocket("/monitoring/logs")
async def service_logs_ws(websocket: WebSocket):
    """WebSocket endpoint for service logs."""
    await websocket.accept()
    try:
        while True:
            # Monitor log files and send updates
            log_entry = await monitor_service_logs()
            if log_entry:  # Only send if there's new data
                await websocket.send_json(log_entry)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        logger.info("Client disconnected from service logs")


@app.get("/health")
async def ui_health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "uptime": get_uptime(),
        "memory_usage": get_memory_usage()
    }
