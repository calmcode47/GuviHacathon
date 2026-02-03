"""Audio quality assessment module."""
from typing import Dict
import numpy as np
from app.utils.audio import PCMDecodeResult


def assess_audio_quality(pcm: PCMDecodeResult) -> Dict[str, float]:
    """
    Assess audio quality and return metrics.
    
    Returns a dictionary with quality metrics:
    - qualityScore: Overall quality score (0.0 to 1.0)
    - sampleRate: Sample rate in Hz
    - duration: Duration in seconds
    - channels: Number of channels
    - isValidFormat: Whether format is valid
    """
    # Base quality score starts at 1.0
    quality_score = 1.0
    
    # Penalize short audio
    if pcm.short_audio:
        quality_score *= 0.6
    
    # Penalize suspect sample rates
    if pcm.sample_rate_suspect:
        quality_score *= 0.85
    
    # Penalize invalid format
    if not pcm.format_valid:
        quality_score *= 0.9
    
    # Check for reasonable duration (1-60 seconds is ideal)
    if pcm.duration_seconds < 0.5:
        quality_score *= 0.5
    elif pcm.duration_seconds < 1.0:
        quality_score *= 0.7
    elif pcm.duration_seconds > 60:
        quality_score *= 0.9
    
    # Check sample rate quality (16kHz-48kHz is ideal)
    if pcm.sample_rate < 8000:
        quality_score *= 0.6
    elif pcm.sample_rate < 16000:
        quality_score *= 0.8
    elif pcm.sample_rate > 48000:
        quality_score *= 0.95
    
    # Check for silence or very low energy
    if pcm.waveform_int16.size > 0:
        max_amplitude = np.max(np.abs(pcm.waveform_int16))
        if max_amplitude < 100:  # Very quiet
            quality_score *= 0.7
    
    return {
        "qualityScore": float(np.clip(quality_score, 0.0, 1.0)),
        "sampleRate": pcm.sample_rate,
        "duration": pcm.duration_seconds,
        "channels": pcm.channels,
        "isValidFormat": pcm.format_valid,
    }
