# service_ui/run.py
"""Service UI launcher with API services."""

import signal
import subprocess
import sys
from pathlib import Path

import uvicorn

# Service definitions
SERVICES = {
    "config": 8001,
    "communication": 8002,
    "process": 8003,
    "state": 8004,
    "data_collection": 8005,
    "validation": 8006,
    "messaging": 8007
}


class ServiceManager:
    """Manages API service processes."""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        
    def start_service(self, name: str, port: int):
        """Start a service process."""
        try:
            process = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn",
                    f"micro_cold_spray.api.{name}.router:app",
                    "--host", "0.0.0.0",
                    "--port", str(port),
                    "--reload"
                ],
                cwd=str(Path(__file__).parent.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            self.processes[name] = process
            print(f"Started {name} service on port {port}")
            return process
        except Exception as e:
            print(f"Failed to start {name} service: {e}")
            return None

    def start_all(self):
        """Start all API services."""
        for name, port in SERVICES.items():
            self.start_service(name, port)

    def stop_all(self):
        """Stop all running services."""
        self.running = False
        for name, process in self.processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"Stopped {name} service")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"Killed {name} service")
            except Exception as e:
                print(f"Error stopping {name} service: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\nShutting down services...")
    if hasattr(signal_handler, 'manager'):
        signal_handler.manager.stop_all()
    sys.exit(0)


def main():
    """Main entry point."""
    print("Starting MicroColdSpray services...")
    
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start service manager
    manager = ServiceManager()
    signal_handler.manager = manager
    manager.start_all()
    
    # Start UI service
    print("\nStarting Service UI on http://localhost:8000")
    uvicorn.run(
        "service_ui.__main__:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )


if __name__ == "__main__":
    main()
