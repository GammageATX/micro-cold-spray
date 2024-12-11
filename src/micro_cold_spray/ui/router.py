"""Service UI router."""

from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

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
    "process": "http://localhost:8003",
    "state": "http://localhost:8004",
    "data_collection": "http://localhost:8005",
    "validation": "http://localhost:8006",
    "messaging": "http://localhost:8007"
}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Render home page."""
    return templates.TemplateResponse(
        "base.html",
        {
            "request": request,
            "api_urls": API_URLS
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
            "api_urls": API_URLS
        }
    )


@app.get("/communication/equipment", response_class=HTMLResponse)
async def equipment_control(request: Request):
    """Render equipment control page."""
    return templates.TemplateResponse(
        "communication/equipment.html",
        {
            "request": request,
            "api_urls": API_URLS
        }
    )


@app.get("/communication/tags", response_class=HTMLResponse)
async def tag_monitor(request: Request):
    """Render tag monitor page."""
    return templates.TemplateResponse(
        "communication/tags.html",
        {
            "request": request,
            "api_urls": API_URLS
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
            "api_urls": API_URLS
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
            "api_urls": API_URLS
        }
    )


@app.get("/process/patterns", response_class=HTMLResponse)
async def pattern_editor(request: Request):
    """Render pattern editor page."""
    return templates.TemplateResponse(
        "process/patterns.html",
        {
            "request": request,
            "api_urls": API_URLS
        }
    )


@app.get("/process/sequences", response_class=HTMLResponse)
async def sequence_control(request: Request):
    """Render sequence control page."""
    return templates.TemplateResponse(
        "process/sequences.html",
        {
            "request": request,
            "api_urls": API_URLS
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
            "api_urls": API_URLS
        }
    )
