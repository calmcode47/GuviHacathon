import base64
import io
from urllib.parse import urlparse
import requests

MP3_MAGIC_HEADERS = [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
UA = "VoiceDetector/1.0 (+https://railway.app)"


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
    Strictly online: no local fallbacks.
    """
    if not _validate_url(url):
        raise ValueError("Invalid URL format")
    try:
        r = requests.get(url, timeout=30, stream=True, headers={"User-Agent": UA})
    except requests.exceptions.Timeout:
        raise TimeoutError("Download timeout after 30s")
    except Exception as e:
        raise RuntimeError(f"Download failed: {str(e)}")
    if r.status_code != 200:
        raise RuntimeError(f"Download failed: HTTP {r.status_code}")
    ctype = r.headers.get("Content-Type", "")
    # Allow if audio or mpeg; otherwise continue but rely on magic header
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
        raise ValueError("File is not MP3 format")
    return base64.b64encode(data).decode("ascii")
