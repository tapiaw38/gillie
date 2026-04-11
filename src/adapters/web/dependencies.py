from fastapi import Request
from src.core.use_cases.use_cases import Usecases


def get_usecases(request: Request) -> Usecases:
    """FastAPI dependency — reads usecases from app.state set at startup."""
    return request.app.state.usecases
