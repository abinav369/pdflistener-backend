"""
Conversion service: PDF/DOCX → text → audio

Pipeline:
1. Extract text from the uploaded document (PyMuPDF for PDF, python-docx for Word)
2. Convert text to speech (gTTS by default; swap to openai TTS for higher quality)
3. Return the path to the generated MP3 file
"""
import os
import uuid
import math
import logging
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Text Extraction ───────────────────────────────────────────────────────────

def extract_text_from_pdf(file_path: str) -> str:
    """Extract plain text from a PDF using PyMuPDF (fitz)."""
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(file_path)
        text = "\n".join(page.get_text() for page in doc)
        doc.close()
        return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError(f"Could not extract text from PDF: {e}")


def extract_text_from_docx(file_path: str) -> str:
    """Extract plain text from a .docx file."""
    try:
        from docx import Document
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e:
        logger.error(f"DOCX extraction failed: {e}")
        raise RuntimeError(f"Could not extract text from DOCX: {e}")


def extract_text(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Text-to-Speech ────────────────────────────────────────────────────────────

def _tts_gtts(text: str, output_path: str) -> None:
    """Convert text to MP3 using Google Text-to-Speech (free, requires internet)."""
    from gtts import gTTS
    # gTTS has a ~5000 char limit per request; split if needed
    MAX_CHARS = 4500
    chunks = [text[i:i + MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]

    if len(chunks) == 1:
        tts = gTTS(text=chunks[0], lang="en", slow=False)
        tts.save(output_path)
    else:
        import tempfile
        from pydub import AudioSegment
        parts = []
        for idx, chunk in enumerate(chunks):
            tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
            gTTS(text=chunk, lang="en", slow=False).save(tmp.name)
            parts.append(AudioSegment.from_mp3(tmp.name))
            os.unlink(tmp.name)
        combined = sum(parts)
        combined.export(output_path, format="mp3")


def _tts_openai(text: str, output_path: str) -> None:
    """Convert text to MP3 using OpenAI TTS (higher quality, requires API key)."""
    from openai import OpenAI
    client = OpenAI(api_key=settings.OPENAI_API_KEY)
    response = client.audio.speech.create(
        model="tts-1",
        voice="alloy",
        input=text[:4096],  # OpenAI limit per call
    )
    response.stream_to_file(output_path)


def text_to_speech(text: str, output_path: str) -> None:
    if settings.TTS_ENGINE == "openai" and settings.OPENAI_API_KEY:
        _tts_openai(text, output_path)
    else:
        _tts_gtts(text, output_path)


# ── Duration Helpers ──────────────────────────────────────────────────────────

def get_audio_duration_seconds(audio_path: str) -> float:
    """Return duration in seconds using mutagen (lightweight)."""
    try:
        from mutagen.mp3 import MP3
        audio = MP3(audio_path)
        return audio.info.length
    except Exception:
        # Fallback: estimate ~130 words/min, ~5 chars/word
        return 0.0


def format_duration(seconds: float) -> str:
    """Convert seconds → '18 min' or '1 hr 5 min'."""
    mins = math.ceil(seconds / 60)
    if mins < 60:
        return f"{mins} min"
    hrs = mins // 60
    rem = mins % 60
    return f"{hrs} hr {rem} min" if rem else f"{hrs} hr"


# ── Main Entry Point ──────────────────────────────────────────────────────────

def convert_document_to_audio(file_path: str) -> dict:
    """
    Full pipeline: document → text → audio.

    Returns:
        {
            "audio_path": str,
            "duration_seconds": float,
            "duration_str": str,
        }
    """
    text = extract_text(file_path)
    if not text:
        text = "This document appears to contain no readable text. It might be an image-based scan."

    audio_filename = f"{uuid.uuid4().hex}.mp3"
    audio_path = os.path.join(settings.AUDIO_OUTPUT_DIR, audio_filename)

    text_to_speech(text, audio_path)

    duration_seconds = get_audio_duration_seconds(audio_path)

    return {
        "audio_path": audio_path,
        "duration_seconds": duration_seconds,
        "duration_str": format_duration(duration_seconds),
    }
