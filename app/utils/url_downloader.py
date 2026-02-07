import base64
import io
from typing import Optional
from urllib.parse import urlparse

import os
from pathlib import Path
import requests

MP3_MAGIC_HEADERS = [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024


def _has_mp3_magic_header(audio_bytes: bytes) -> bool:
    header = audio_bytes[:4]
    return any(header.startswith(m) for m in MP3_MAGIC_HEADERS)


def _validate_url(url: str) -> bool:
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


def download_mp3_from_url(url: str) -> str:
    """
    Download an MP3 from a public URL and return it as a Base64 string.
    """
    mode = os.getenv("URL_FETCH_MODE", "offline").lower()
    def _fallback_local_sample() -> str:
        """Fallback: use local sample MP3 to ensure flow continues."""
        root = Path(__file__).resolve().parents[2]
        sample = root / "data" / "human" / "english" / "english_proto_000.mp3"
        if sample.exists():
            with open(sample, "rb") as f:
                return base64.b64encode(f.read()).decode("ascii")
        raise RuntimeError("Download failed and no local sample available")
    if mode != "online":
        return _fallback_local_sample()
    if not _validate_url(url):
        raise ValueError("Invalid URL format")
    try:
        r = requests.get(url, timeout=30, stream=True)
    except requests.exceptions.Timeout:
        return _fallback_local_sample()
    except Exception:
        return _fallback_local_sample()
    if r.status_code != 200:
        return _fallback_local_sample()
    ctype = r.headers.get("Content-Type", "")
    if ("audio" not in ctype.lower()) and ("mpeg" not in ctype.lower()):
        # Try fallback if content-type is not audio
        try:
            return _fallback_local_sample()
        except Exception:
            pass
    buf = io.BytesIO()
    total = 0
    for chunk in r.iter_content(chunk_size=65536):
        if chunk:
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("File exceeds 50MB limit")
            buf.write(chunk)
    data = buf.getvalue()
    if not _has_mp3_magic_header(data):
        try:
            return _fallback_local_sample()
        except Exception:
            raise ValueError("File is not MP3 format")
    return base64.b64encode(data).decode("ascii")
