"""Health + channel-status routes."""
from fastapi import APIRouter

from ..config import channel_status, settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/channels")
def channels():
    """Tell the frontend which channels are wired up."""
    return {
        "status": channel_status(),
        "sender": {
            "name": settings.sender_name,
            "company": settings.sender_company,
            "role": settings.sender_role,
        },
    }
