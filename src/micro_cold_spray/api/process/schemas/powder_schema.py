"""Powder schema definition."""

from enum import Enum
from pydantic import BaseModel, Field


class PowderMorphology(str, Enum):
    """Powder morphology types."""
    SPHERICAL = "spherical"
    IRREGULAR = "irregular"
    DENDRITIC = "dendritic"


class SizeRange(BaseModel):
    """Powder size range."""
    min: float = Field(gt=0, description="Minimum particle size (μm)")
    max: float = Field(gt=0, description="Maximum particle size (μm)")


class Powder(BaseModel):
    """Powder definition."""
    name: str = Field(description="Powder name")
    material: str = Field(description="Powder material")
    size_range: SizeRange = Field(description="Particle size range")
    morphology: PowderMorphology = Field(description="Powder morphology")


class PowderData(BaseModel):
    """Powder file structure."""
    powder: Powder
