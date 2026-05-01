from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class NotificationType(str, enum.Enum):
    CONVERSION_COMPLETE = "conversion_complete"
    CONVERSION_FAILED = "conversion_failed"
    STORAGE_WARNING = "storage_warning"
    SYSTEM = "system"


class NotificationItem(Base):
    __tablename__ = "notification_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Mirrors Dart NotificationItem fields
    title = Column(String, nullable=False)
    message = Column(String, nullable=False)
    time = Column(String, nullable=False)     # human-readable, e.g. "2 hours ago"
    unread = Column(Boolean, default=True)
    type = Column(Enum(NotificationType), default=NotificationType.SYSTEM)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="notifications")
