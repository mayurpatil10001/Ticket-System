"""Saved replies API — thin wrapper (actual endpoints are in settings_api.py)."""
# This file exists so main.py can include it; settings_api already registers these.
from fastapi import APIRouter
router = APIRouter()  # empty — settings_api handles saved-replies endpoints
