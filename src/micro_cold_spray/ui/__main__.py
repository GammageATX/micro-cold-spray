"""UI service launcher for standalone UI mode."""

import uvicorn


def main():
    """Start the UI service only."""
    print("Starting MicroColdSpray UI in standalone mode...")
    print("Note: API services must be started separately")
    
    uvicorn.run(
        "micro_cold_spray.ui.router:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Default to False since we can't await in sync context
        log_level="info"
    )


if __name__ == "__main__":
    main()
