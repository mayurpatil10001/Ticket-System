"""Internal tickets API — thin wrapper (actual endpoints are in actions_api.py)."""
from fastapi import APIRouter
router = APIRouter()  # empty — actions_api handles internal-ticket endpoints
