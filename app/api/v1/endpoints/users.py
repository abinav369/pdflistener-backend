from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UpdateUserRequest

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return the authenticated user's profile (used by the Settings screen)."""
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UpdateUserRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update user profile — called by the Settings screen when the user
    changes their name, toggles Dark Mode, or toggles Notifications.
    """
    if payload.name is not None:
        current_user.name = payload.name
    if payload.notifications_enabled is not None:
        current_user.notifications_enabled = payload.notifications_enabled
    if payload.dark_mode is not None:
        current_user.dark_mode = payload.dark_mode

    db.commit()
    db.refresh(current_user)
    return current_user
