"""UI service router for system monitoring and control."""

from typing import Dict, Any
from fastapi import FastAPI, HTTPException, status, Request
from loguru import logger

from .utils import get_template_context


def register_routes(app: FastAPI) -> None:
    """Register routes with the FastAPI application."""

    @app.get("/")
    async def get_index(request: Request):
        """Serve the system overview dashboard."""
        try:
            return request.app.state.templates.TemplateResponse(
                "dashboard.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": "System Dashboard"
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve dashboard: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/services")
    async def get_services(request: Request):
        """Service health monitoring page."""
        try:
            return request.app.state.templates.TemplateResponse(
                "services.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": "Service Health"
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve services page: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/tags")
    async def get_tag_monitor(request: Request):
        """Advanced tag monitoring and control."""
        try:
            return request.app.state.templates.TemplateResponse(
                "monitoring/tags.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": "Tag Monitor"
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve tag monitor: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/tags/write/{tag_path}")
    async def get_tag_write(request: Request, tag_path: str):
        """Tag write interface."""
        try:
            return request.app.state.templates.TemplateResponse(
                "tag_write.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": f"Write Tag: {tag_path}",
                    "tag_path": tag_path
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve tag write interface: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/config/edit/{config_type}")
    async def get_config_editor(request: Request, config_type: str):
        """Configuration file editor."""
        try:
            return request.app.state.templates.TemplateResponse(
                "config_editor.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": f"Edit Configuration: {config_type}",
                    "config_type": config_type
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve config editor: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/config/history/{config_type}")
    async def get_config_history(request: Request, config_type: str):
        """Configuration change history."""
        try:
            return request.app.state.templates.TemplateResponse(
                "config_history.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": f"Configuration History: {config_type}",
                    "config_type": config_type
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve config history: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/system/state")
    async def get_system_state(request: Request):
        """Detailed system state monitoring."""
        try:
            return request.app.state.templates.TemplateResponse(
                "system_state.html",
                get_template_context(request, {
                    "api_urls": request.app.state.api_endpoints,
                    "title": "System State"
                })
            )
        except Exception as e:
            logger.error(f"Failed to serve system state: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(e)
            )

    @app.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "service": "ui",
            "version": "1.0.0"
        }

    @app.get("/api/config")
    async def get_ui_config(request: Request) -> Dict[str, Any]:
        """Get UI configuration."""
        return {
            "title": "Micro Cold Spray System Control",
            "version": "1.0.0",
            "api_endpoints": request.app.state.api_endpoints,
            "features": {
                "tag_write_enabled": True,
                "config_edit_enabled": True,
                "real_time_updates": True
            }
        }

    # Error handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> Dict[str, Any]:
        """Handle HTTP exceptions."""
        return {
            "status": "error",
            "code": exc.status_code,
            "message": str(exc.detail)
        }

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception) -> Dict[str, Any]:
        """Handle general exceptions."""
        logger.error(f"Unhandled exception: {exc}")
        return {
            "status": "error",
            "code": 500,
            "message": "Internal server error"
        }
