import base64
import io
from urllib.parse import urlparse
import requests

MP3_MAGIC_HEADERS = [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]
MAX_DOWNLOAD_BYTES = 50 * 1024 * 1024
UA = "VoiceDetector/1.0 (+https://railway.app)"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)


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
    parsed = urlparse(url)
    referer = f"{parsed.scheme}://{parsed.netloc}/"
    headers_primary = {
        "User-Agent": UA,
        "Accept": "audio/mpeg,audio/*;q=0.9,*/*;q=0.8",
        "Referer": referer,
    }
    sess = requests.Session()
    # First attempt
    try:
        r = sess.get(url, timeout=30, stream=True, headers=headers_primary, allow_redirects=True)
    except requests.exceptions.Timeout:
        raise TimeoutError("Download timeout after 30s")
    except Exception as e:
        raise RuntimeError(f"Download failed: {str(e)}")
    if r.status_code == 403:
        # Retry once with browser-like headers
        headers_retry = {
            "User-Agent": BROWSER_UA,
            "Accept": "*/*",
            "Referer": referer,
        }
        try:
            r = sess.get(url, timeout=30, stream=True, headers=headers_retry, allow_redirects=True)
        except requests.exceptions.Timeout:
            raise TimeoutError("Download timeout after 30s")
        except Exception as e:
            raise RuntimeError(f"Download failed: {str(e)}")
    if r.status_code != 200:
        raise RuntimeError(f"Download failed: HTTP {r.status_code}")
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
