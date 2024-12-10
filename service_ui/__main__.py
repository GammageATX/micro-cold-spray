# service_ui/main.py
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse

app = FastAPI(title="MicroColdSpray Service UI")

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# API Base URLs
API_URLS = {
    'communication': 'http://localhost:8001',
    'process': 'http://localhost:8002',
    'config': 'http://localhost:8003',
    'state': 'http://localhost:8004',
    'validation': 'http://localhost:8005'
}

@app.get("/")
async def root(request: Request):
    return RedirectResponse(url="/communication/tags")

@app.get("/communication/tags")
async def tags_page(request: Request):
    return templates.TemplateResponse(
        "communication/tags.html", 
        {"request": request, "api_urls": API_URLS}
    )

@app.get("/communication/equipment")
async def equipment_page(request: Request):
    return templates.TemplateResponse(
        "communication/equipment.html", 
        {"request": request, "api_urls": API_URLS}
    )

@app.get("/communication/motion")
async def motion_page(request: Request):
    return templates.TemplateResponse(
        "communication/motion.html", 
        {"request": request, "api_urls": API_URLS}
    )