#!/bin/bash

# Run tests with coverage
pytest tests/ \
    --cov=micro_cold_spray \
    --cov-report=term-missing \
    --cov-report=html \
    -v 