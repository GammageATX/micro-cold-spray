from setuptools import setup, find_packages

setup(
    name="micro-cold-spray",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=[
        "PyQt6>=6.4.0",
        "PySide6>=6.4.0",
        "pyyaml>=6.0.1",
        "paramiko>=3.4.0",
        "loguru>=0.7.0",
        "productivity>=0.11.1",
        "productivity @ git+https://github.com/numat/productivity.git",
    ],
    extras_require={
        "dev": [
            "black>=23.3.0",
            "flake8>=6.0.0",
            "mypy>=1.3.0",
            "pylint>=2.17.0",
            "pytest>=7.3.1",
            "pytest-asyncio>=0.21.0",
            "pytest-qt>=4.2.0",
            "pytest-cov>=4.0.0",
            "pytest-mock>=3.10.0",
        ],
        "docs": [
            "sphinx>=7.0.1",
            "sphinx-rtd-theme>=1.2.0",
            "sphinx-autodoc-typehints>=1.23.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "micro-cold-spray=micro_cold_spray.__main__:main",
        ],
    },
    author="Michael Gammage",
    author_email="gammageatx@gmail.com",
    description="Micro Cold Spray Control System",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    keywords="cold spray, manufacturing, automation, control system",
    url="https://github.com/GammageATX/micro-cold-spray",
    project_urls={
        "Bug Tracker": "https://github.com/GammageATX/micro-cold-spray/issues",
        "Documentation": "https://github.com/GammageATX/micro-cold-spray/wiki",
        "Source Code": "https://github.com/GammageATX/micro-cold-spray",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Manufacturing",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Control",
    ],
)
