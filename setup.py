from setuptools import setup, find_packages

setup(
    name="micro-cold-spray",
    version="0.1",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "fastapi",
        "uvicorn",
        "jinja2",
        "aiofiles",
        "psutil",
        "pyyaml",
        "aiohttp"
    ]
)
