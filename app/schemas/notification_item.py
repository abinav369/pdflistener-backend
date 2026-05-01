from pydantic import BaseModel
from datetime import datetime
from app.models.notification_item import NotificationType


class NotificationItemResponse(BaseModel):
    """Matches the Dart NotificationItem model."""
    id: int
    title: str
    message: str
    time: str       # e.g. "2 hours ago"
    unread: bool
    type: NotificationType

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    items: list[NotificationItemResponse]
    unread_count: int
