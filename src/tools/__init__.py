"""MCP Tool routers for biometrics, workouts, nutrition, and composite analytics."""

from src.tools.biometrics_tools import biometrics_router
from src.tools.composite_tools import composite_router
from src.tools.nutrition_tools import nutrition_router
from src.tools.workout_tools import workout_router

__all__ = [
    "biometrics_router",
    "composite_router",
    "nutrition_router",
    "workout_router",
]
