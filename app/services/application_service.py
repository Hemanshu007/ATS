import structlog
from fastapi import HTTPException

from app.core.constants import ALLOWED_STATUS_TRANSITIONS

log = structlog.get_logger("ats.application")


def validate_status_transition(current_status: str, new_status: str) -> None:
    if new_status == current_status:
        log.warn("status.no_op", current=current_status, requested=new_status)
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'. "
                   f"No-op transitions are not permitted.",
        )
    allowed = ALLOWED_STATUS_TRANSITIONS.get(current_status, [])
    if new_status not in allowed:
        log.warn(
            "status.invalid_transition",
            current=current_status,
            requested=new_status,
            allowed=allowed,
        )
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from '{current_status}' to '{new_status}'. "
                   f"Allowed transitions: {allowed}",
        )
    log.info("status.transition", current=current_status, new=new_status)
