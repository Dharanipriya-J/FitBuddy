"""Pydantic models for request validation."""
from typing import Literal
from pydantic import BaseModel, Field, field_validator

Intensity = Literal["low", "medium", "high"]


def _normalize_intensity(v):
    return v.strip().lower() if isinstance(v, str) else v


class UserInput(BaseModel):
    user_id: int = Field(..., gt=0)
    username: str = Field(..., min_length=1, max_length=60)
    age: int = Field(..., ge=10, le=100)
    weight: float = Field(..., gt=20, le=400, description="Weight in kg")
    goal: str = Field(..., min_length=2, max_length=200)
    intensity: Intensity

    _norm = field_validator("intensity", mode="before")(_normalize_intensity)


class FeedbackRequest(BaseModel):
    feedback: str = Field(..., min_length=3, max_length=500)


class WorkoutRequest(BaseModel):
    goal: str = Field(..., min_length=2, max_length=200)
    intensity: Intensity

    _norm = field_validator("intensity", mode="before")(_normalize_intensity)
