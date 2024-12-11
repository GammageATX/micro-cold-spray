@app.get("/health")
async def health_check():
    """Check API health."""
    try:
        if validation_service is None:
            return {
                "status": "Error",
                "error": "Service not initialized"
            }
        return {
            "status": "Running",
            "error": None
        }
    except Exception as e:
        return {
            "status": "Error",
            "error": str(e)
        }
