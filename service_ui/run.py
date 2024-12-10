# service_ui/run.py
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "service_ui.__main__:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )