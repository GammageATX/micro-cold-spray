from setuptools import setup, find_packages

setup(
    name="micro-cold-spray",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "fastapi>=0.104.1",
        "uvicorn>=0.24.0",
        "jinja2>=3.1.2",
        "aiofiles>=23.2.1",
        "python-multipart>=0.0.6",
        "pyyaml>=6.0.1",
        "loguru>=0.7.0",
        "dynaconf>=3.2.4",
        "pydantic>=2.5.2",
        "httpx>=0.25.2",
        "websockets>=12.0",
        "productivity @ git+https://github.com/numat/productivity.git",
    ],
    extras_require={
        "dev": [
            "black>=23.3.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.0.0",
            "sphinx>=7.0.1",
        ]
    },
    author="Michael Gammage",
    author_email="gammageatx@gmail.com",
    description="Micro Cold Spray Control System",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)
