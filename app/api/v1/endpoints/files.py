import os
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.file_item import FileItem, ProcessingStatus
from app.schemas.file_item import FileItemResponse, FileItemListResponse
from app.services.conversion import convert_document_to_audio, format_duration
from app.services.notifications import (
    create_conversion_complete_notification,
    create_conversion_failed_notification,
)

router = APIRouter()
logger = logging.getLogger(__name__)


def _human_size(size_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _format_date(dt: datetime) -> str:
    return dt.strftime("%b %d, %Y")


def _enrich(file: FileItem, request_base_url: str = "") -> FileItemResponse:
    """Add computed fields before serialization."""
    audio_url = None
    if file.audio_path and os.path.exists(file.audio_path):
        audio_url = f"/api/v1/files/{file.id}/audio"
    return FileItemResponse(
        id=file.id,
        title=file.title,
        size=file.size,
        duration=file.duration,
        date=file.date,
        status=file.status,
        audio_url=audio_url,
        created_at=file.created_at,
    )


def _run_conversion(file_id: int, db: Session) -> None:
    """Background task: convert document → audio and update DB."""
    file = db.query(FileItem).filter(FileItem.id == file_id).first()
    if not file:
        return

    file.status = ProcessingStatus.PROCESSING
    db.commit()

    try:
        result = convert_document_to_audio(file.original_path)
        file.audio_path = result["audio_path"]
        file.duration_seconds = result["duration_seconds"]
        file.duration = result["duration_str"]
        file.status = ProcessingStatus.COMPLETED
        db.commit()
        create_conversion_complete_notification(db, file.user_id, file.title)
    except Exception as e:
        logger.error(f"Conversion failed for file {file_id}: {e}")
        file.status = ProcessingStatus.FAILED
        db.commit()
        create_conversion_failed_notification(db, file.user_id, file.title)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=FileItemResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a PDF, DOC, or DOCX file.
    Immediately returns a FileItem with status=pending.
    Conversion runs in the background and the status is updated asynchronously.
    Poll GET /files/{id} to track progress.
    """
    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: .{ext}")

    # Read and validate size
    content = await file.read()
    size_bytes = len(content)
    if size_bytes > settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit")

    # Save to disk
    saved_filename = f"{uuid.uuid4().hex}_{file.filename}"
    saved_path = os.path.join(settings.UPLOAD_DIR, saved_filename)
    with open(saved_path, "wb") as f:
        f.write(content)

    # Derive display title (strip extension)
    title = Path(file.filename).stem.replace("_", " ").replace("-", " ").title()
    now = datetime.now(timezone.utc)

    db_file = FileItem(
        user_id=current_user.id,
        title=title,
        size=_human_size(size_bytes),
        size_bytes=size_bytes,
        date=_format_date(now),
        original_filename=file.filename,
        original_path=saved_path,
        status=ProcessingStatus.PENDING,
    )
    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    # Kick off background conversion
    background_tasks.add_task(_run_conversion, db_file.id, db)

    return _enrich(db_file)


@router.get("/", response_model=FileItemListResponse)
def list_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all files for the current user (Library + Home screen).
    Returns only completed files by default.
    """
    files = (
        db.query(FileItem)
        .filter(FileItem.user_id == current_user.id)
        .order_by(FileItem.created_at.desc())
        .all()
    )
    return FileItemListResponse(
        items=[_enrich(f) for f in files],
        total=len(files),
    )


@router.get("/{file_id}", response_model=FileItemResponse)
def get_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single file — used by the Processing screen to poll for status."""
    file = db.query(FileItem).filter(
        FileItem.id == file_id, FileItem.user_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    return _enrich(file)


@router.get("/{file_id}/audio")
def stream_audio(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream the generated MP3 audio file.
    Used by the Player screen via just_audio's URL source.
    """
    file = db.query(FileItem).filter(
        FileItem.id == file_id, FileItem.user_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")
    if file.status != ProcessingStatus.COMPLETED or not file.audio_path:
        raise HTTPException(status_code=409, detail="Audio not ready yet")
    if not os.path.exists(file.audio_path):
        raise HTTPException(status_code=404, detail="Audio file missing on disk")

    return FileResponse(
        file.audio_path,
        media_type="audio/mpeg",
        filename=f"{file.title}.mp3",
    )


@router.delete("/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a file and its associated audio.
    Triggered by swipe-to-delete in the Library screen.
    """
    file = db.query(FileItem).filter(
        FileItem.id == file_id, FileItem.user_id == current_user.id
    ).first()
    if not file:
        raise HTTPException(status_code=404, detail="File not found")

    # Clean up files on disk
    for path in [file.original_path, file.audio_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    db.delete(file)
    db.commit()
