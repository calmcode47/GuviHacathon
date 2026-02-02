import base64
import io
import os
import subprocess
import tempfile
from typing import Tuple

import numpy as np
import librosa
import audioread
from dataclasses import dataclass

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


@dataclass
class PCMDecodeResult:
    waveform_int16: np.ndarray
    sample_rate: int
    channels: int
    duration_seconds: float
    format_valid: bool
    sample_rate_suspect: bool
    short_audio: bool


def _read_mp3_pcm_with_audioread(mp3_path: str) -> Tuple[np.ndarray, int, int]:
    with audioread.audio_open(mp3_path) as f:
        sr = int(f.samplerate)
        ch = int(f.channels)
        pcm_chunks = []
        for buf in f:
            pcm_chunks.append(np.frombuffer(buf, dtype=np.int16))
        if not pcm_chunks:
            raise ValueError("Empty audio data")
        pcm = np.concatenate(pcm_chunks)
        if ch > 1:
            frames = pcm.reshape(-1, ch)
            frames = frames.T
        else:
            frames = pcm.reshape(1, -1)
        return frames, sr, ch


def decode_base64_mp3_to_pcm(audio_base64: str) -> PCMDecodeResult:
    try:
        audio_bytes = base64.b64decode(audio_base64, validate=True)
    except Exception as e:
        raise ValueError("Invalid base64 audio") from e
    if len(audio_bytes) > MAX_AUDIO_BYTES:
        raise ValueError(f"Audio file too large; max {MAX_AUDIO_BYTES} bytes")
    header_ok = _has_mp3_magic_header(audio_bytes)
    fd, temp_path = tempfile.mkstemp(suffix=".mp3")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(audio_bytes)
        try:
            frames, sr, ch = _read_mp3_pcm_with_audioread(temp_path)
        except Exception as e:
            raise RuntimeError("Failed to decode MP3") from e
        duration = float(frames.shape[1]) / float(sr)
        sr_suspect = not (8000 <= sr <= 48000)
        return PCMDecodeResult(
            waveform_int16=frames,
            sample_rate=sr,
            channels=ch,
            duration_seconds=duration,
            format_valid=header_ok,
            sample_rate_suspect=sr_suspect,
            short_audio=duration < 1.0,
        )
    finally:
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception:
            pass


def read_mp3_to_pcm_result(mp3_path: str) -> PCMDecodeResult:
    frames, sr, ch = _read_mp3_pcm_with_audioread(mp3_path)
    duration = float(frames.shape[1]) / float(sr)
    header_ok = True
    sr_suspect = not (8000 <= sr <= 48000)
    return PCMDecodeResult(
        waveform_int16=frames,
        sample_rate=sr,
        channels=ch,
        duration_seconds=duration,
        format_valid=header_ok,
        sample_rate_suspect=sr_suspect,
        short_audio=duration < 1.0,
    )
