"""Helper to create notifications after conversion events."""
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models.notification_item import NotificationItem, NotificationType


def _relative_time(dt: datetime) -> str:
    return "Just now"


def create_conversion_complete_notification(db: Session, user_id: int, file_title: str) -> None:
    notif = NotificationItem(
        user_id=user_id,
        title="Conversion Complete",
        message=f'"{file_title}" is ready to listen.',
        time=_relative_time(datetime.now(timezone.utc)),
        unread=True,
        type=NotificationType.CONVERSION_COMPLETE,
    )
    db.add(notif)
    db.commit()


def create_conversion_failed_notification(db: Session, user_id: int, file_title: str) -> None:
    notif = NotificationItem(
        user_id=user_id,
        title="Conversion Failed",
        message=f'Could not convert "{file_title}". Please try again.',
        time=_relative_time(datetime.now(timezone.utc)),
        unread=True,
        type=NotificationType.CONVERSION_FAILED,
    )
    db.add(notif)
    db.commit()
