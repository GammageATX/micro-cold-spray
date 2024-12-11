"""Service UI main module."""

# Standard library imports
import asyncio
import os
import subprocess
import sys
from pathlib import Path

# Third-party imports
import aiohttp
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Get base directory
BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(title="MicroColdSpray Service UI")

# Mount static files
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# API Base URLs and ports
API_PORTS = {
    'config': 8003,  # Just Config API for now
}

API_URLS = {
    service: f'http://localhost:{port}'
    for service, port in API_PORTS.items()
}


@app.get("/")
@app.get("/config")
async def root(request: Request):
    """Show service dashboard."""
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/communication/tags")
async def tags_page(request: Request):
    """Tag operations page."""
    return templates.TemplateResponse(
        "communication/tags.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/communication/equipment")
async def equipment_page(request: Request):
    """Equipment control page."""
    return templates.TemplateResponse(
        "communication/equipment.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/process/sequences")
async def sequences_page(request: Request):
    """Sequence control page."""
    return templates.TemplateResponse(
        "process/sequences.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/config/editor")
async def editor_page(request: Request):
    """Config editor page."""
    return templates.TemplateResponse(
        "config/editor.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/state/monitor")
async def state_page(request: Request):
    """State monitor page."""
    return templates.TemplateResponse(
        "state/monitor.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/communication/motion")
async def motion_page(request: Request):
    """Motion control page."""
    return templates.TemplateResponse(
        "communication/motion.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/process/patterns")
async def patterns_page(request: Request):
    """Pattern editor page."""
    return templates.TemplateResponse(
        "process/patterns.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/process/parameters")
async def parameters_page(request: Request):
    """Parameter editor page."""
    return templates.TemplateResponse(
        "process/parameters.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.get("/diagnostics/services")
async def services_page(request: Request):
    """Service control page."""
    return templates.TemplateResponse(
        "base.html",
        {"request": request, "api_urls": API_URLS}
    )


@app.post("/service/{service}/{action}")
async def control_service(service: str, action: str):
    """Control service (start/stop/restart)."""
    try:
        print(f"Controlling {service} service: {action}")
        
        service_commands = {
            'config': f'uvicorn micro_cold_spray.api.config.main:app --port {API_PORTS["config"]} --host 0.0.0.0 --log-level debug'
        }

        if action == 'start' or action == 'restart':
            print(f"Starting service: {service_commands[service]}")
            # Start service with output capture
            process = subprocess.Popen(
                service_commands[service].split(),
                cwd=os.getcwd(),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,  # Get string output
                bufsize=1,  # Line buffered
                universal_newlines=True
            )
            
            print(f"Started process: {process.pid}")

            # Check initial output for errors
            try:
                for _ in range(10):  # Check first 10 lines or timeout
                    stderr_line = process.stderr.readline()
                    if stderr_line:
                        print(f"Service error: {stderr_line.strip()}")
                        if "Error" in stderr_line or "Exception" in stderr_line:
                            return {
                                "status": "error",
                                "message": f"Service startup error: {stderr_line.strip()}"
                            }
            except Exception as e:
                print(f"Error reading service output: {e}")

            await asyncio.sleep(2)  # Give it time to start

            # Check if service is responding
            max_retries = 5
            for i in range(max_retries):
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(f"{API_URLS[service]}/health") as response:
                            if response.status == 200:
                                print("Service health check passed")
                                return {
                                    "status": "success",
                                    "message": f"{action} completed for {service}"
                                }
                except Exception as e:
                    print(f"Health check attempt {i+1} failed: {e}")
                    if i < max_retries - 1:
                        await asyncio.sleep(1)
                    else:
                        # Get any error output
                        stderr_output = process.stderr.read()
                        if stderr_output:
                            print(f"Service error output: {stderr_output}")
                        return {
                            "status": "error",
                            "message": f"Service failed to start: {stderr_output or str(e)}"
                        }

        return {
            "status": "success",
            "message": f"{action} completed for {service}"
        }
        
    except Exception as e:
        print(f"Service control error: {e}")
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    print("Starting MicroColdSpray Service UI...")
    print("Open http://localhost:8000 in your browser")
    uvicorn.run(
        "service_ui.__main__:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
