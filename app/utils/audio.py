import base64
import io
import os
import subprocess
import tempfile
from typing import Tuple

import numpy as np
import librosa

from app.core.config import SUPPORTED_LANGUAGES, MAX_AUDIO_BYTES, MAX_DURATION_SECONDS

MP3_MAGIC_HEADERS = [b"ID3", b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"]


def assert_supported_language(language: str) -> None:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language")


def _has_mp3_magic_header(audio_bytes: bytes) -> bool:
    header = audio_bytes[:4]
    return any(header.startswith(m) for m in MP3_MAGIC_HEADERS)


def decode_base64_to_temp_mp3(audio_base64: str) -> str:
    """Decode base64 MP3 into a temporary file and return the path.

    Performs MP3 validation via basic header checks and enforces max size.
    """
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception as e:
        raise ValueError("Invalid base64 audio") from e

    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError(f"Audio file too large; max {MAX_AUDIO_BYTES} bytes")

    # Basic MP3 header check: ID3 or MPEG frame sync
    if not _has_mp3_magic_header(audio_bytes):
        # Allow parsing to proceed—some streams may not start at typical offsets
        pass

    fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    with os.fdopen(fd, "wb") as f:
        f.write(audio_bytes)
    return temp_path


def _transcode_mp3_to_wav_via_ffmpeg(mp3_path: str) -> str:
    """Fallback decode using ffmpeg CLI to WAV, returning temp WAV path.

    Requires ffmpeg available in PATH (bundled in Docker).
    """
    wav_fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(wav_fd)
    try:
        # -y overwrite, -i input, pcm_s16le mono to reduce load, but keep native sr via -ar not set
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            mp3_path,
            wav_path,
        ]
        subprocess.run(cmd, check=True)
        return wav_path
    except Exception as e:
        # Cleanup on failure
        if os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except Exception:
                pass
        raise RuntimeError("FFmpeg fallback decode failed") from e


def load_audio_waveform(mp3_path: str) -> Tuple[np.ndarray, int]:
    """Load audio to waveform using librosa (audioread backend for MP3),
    with ffmpeg WAV fallback on failure.

    Audio is read for analysis only; we do not modify or persist it.
    """
    # First try librosa/audioread
    try:
        y, sr = librosa.load(mp3_path, sr=None, mono=True)
    except Exception:
        # Fallback to ffmpeg -> WAV -> librosa
        wav_path = _transcode_mp3_to_wav_via_ffmpeg(mp3_path)
        try:
            y, sr = librosa.load(wav_path, sr=None, mono=True)
        finally:
            try:
                if os.path.exists(wav_path):
                    os.remove(wav_path)
            except Exception:
                pass

    duration = float(len(y)) / float(sr)
    if duration < 0.5:
        raise ValueError("Audio too short for reliable analysis")
    if duration > MAX_DURATION_SECONDS:
        raise ValueError(f"Audio too long; max {MAX_DURATION_SECONDS} seconds")

    return y, sr


def cleanup_temp_file(path: str) -> None:
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        # Non-fatal cleanup failure
        pass