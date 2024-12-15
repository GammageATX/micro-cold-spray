from setuptools import setup, find_packages

setup(
    name="micro_cold_spray",
    version="1.0.0",
    packages=find_packages("src"),
    package_dir={"": "src"},
    include_package_data=True,
    package_data={
        "micro_cold_spray.ui": [
            "static/**/*",
            "templates/**/*",
        ],
    },
    install_requires=[
        # Core Dependencies
        "PyQt6>=6.4.0",
        "PySide6>=6.4.0",
        "pyyaml>=6.0.1",
        "paramiko>=3.4.0",
        "loguru>=0.7.0",
        "productivity>=0.11.1",
        
        # API Dependencies
        "fastapi>=0.95.0",
        "uvicorn>=0.22.0",
        "jinja2>=3.1.2",
        "python-multipart>=0.0.6",
        "aiofiles>=23.2.1",
        "websockets>=12.0",
        "httpx>=0.24.0",
        
        # Additional Dependencies
        "asyncssh>=2.13.2",
        "pydantic>=2.0.0",
        "typing_extensions>=4.0.0",
        "jsonschema>=4.17.3",
        "psutil>=5.9.0",
    ],
    extras_require={
        "dev": [
            # Testing
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
            
            # Development Tools
            "black>=23.3.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
            "pylint>=2.17.0",
            
            # Documentation
            "sphinx>=7.0.1",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.23.0",
        ]
    },
    python_requires=">=3.9",
)
