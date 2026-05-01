from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.notification_item import NotificationItem
from app.schemas.notification_item import NotificationListResponse, NotificationItemResponse

router = APIRouter()


@router.get("/", response_model=NotificationListResponse)
def list_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return all notifications for the current user (Notifications screen)."""
    notifications = (
        db.query(NotificationItem)
        .filter(NotificationItem.user_id == current_user.id)
        .order_by(NotificationItem.created_at.desc())
        .all()
    )
    unread_count = sum(1 for n in notifications if n.unread)
    return NotificationListResponse(
        items=notifications,
        unread_count=unread_count,
    )


@router.post("/mark-all-read", response_model=NotificationListResponse)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read — triggered by 'Mark All Read' button."""
    db.query(NotificationItem).filter(
        NotificationItem.user_id == current_user.id,
        NotificationItem.unread == True,
    ).update({"unread": False})
    db.commit()

    notifications = (
        db.query(NotificationItem)
        .filter(NotificationItem.user_id == current_user.id)
        .order_by(NotificationItem.created_at.desc())
        .all()
    )
    return NotificationListResponse(items=notifications, unread_count=0)


@router.patch("/{notification_id}/read", response_model=NotificationItemResponse)
def mark_one_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single notification as read (mirrors copyWith unread=false logic)."""
    notif = db.query(NotificationItem).filter(
        NotificationItem.id == notification_id,
        NotificationItem.user_id == current_user.id,
    ).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.unread = False
    db.commit()
    db.refresh(notif)
    return notif
