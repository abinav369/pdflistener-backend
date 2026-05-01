from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.core.database import Base


class ProcessingStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class FileItem(Base):
    __tablename__ = "file_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Mirrors Dart FileItem fields
    title = Column(String, nullable=False)          # document filename / title
    size = Column(String, nullable=False)           # human-readable, e.g. "2.4 MB"
    duration = Column(String, nullable=True)        # audio duration, e.g. "18 min"
    date = Column(String, nullable=False)           # display date, e.g. "Jan 15, 2025"

    # Backend-specific fields
    original_filename = Column(String, nullable=False)
    original_path = Column(String, nullable=False)  # path to uploaded file
    audio_path = Column(String, nullable=True)      # path to generated audio
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    size_bytes = Column(Float, nullable=False)
    duration_seconds = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    owner = relationship("User", back_populates="files")
