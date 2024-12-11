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
        "fastapi",
        "uvicorn",
        "jinja2",
        "python-multipart",
        "aiofiles",
        "websockets",
        "loguru",
        "asyncssh",
        "pydantic",
        "typing_extensions",
    ],
    python_requires=">=3.7",
)
