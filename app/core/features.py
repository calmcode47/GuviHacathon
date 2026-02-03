"""
Canonical feature list for voice detection (human vs AI).
Used by: classifier, detector aggregation, data_loader, train_model, train.
"""
from typing import List

FEATURE_NAMES: List[str] = [
    "pitch_var",
    "jitter_proxy",
    "hnr_ratio",
    "spectral_flatness_mean",
    "spectral_rolloff_median",
    "phase_coherence_median",
    "energy_entropy_norm",
    "temporal_discontinuity_rate",
    "prosody_pause_std",
    "voiced_ratio",
]
