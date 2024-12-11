"""Config API for managing configuration files."""

import yaml
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI(title="Config API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Config directory - use workspace root config directory
CONFIG_DIR = Path(__file__).parents[4] / "config"
CONFIG_DIR.mkdir(exist_ok=True) 