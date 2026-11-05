from __future__ import annotations

from fastapi import APIRouter

from . import coverage, data_quality, geo, health, models, municipalities, predictions

api_router = APIRouter(prefix="/api/v1")
for module in (health, coverage, municipalities, predictions, models, data_quality, geo):
    api_router.include_router(module.router)
