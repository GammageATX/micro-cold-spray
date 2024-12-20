"""Configuration service application."""

from micro_cold_spray.api.config.config_service import create_config_service

app = create_config_service()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
