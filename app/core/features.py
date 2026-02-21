"""
Canonical feature list for voice detection (human vs AI).
Used by: classifier, detector aggregation, data_loader, train_model, train.
"""
from typing import List

FEATURE_NAMES: List[str] = [
    "pitch_var",
    "jitter_proxy",
    "shimmer",
    "hnr_ratio",
    "spectral_flatness_mean",
    "spectral_rolloff_median",
    "spectral_flux_mean",
    "phase_coherence_median",
    "energy_entropy_norm",
    "temporal_discontinuity_rate",
    "prosody_pause_std",
    "syllable_rate",
    "onset_env_std",
    "mfcc_std_mean",
    "f0_stability",
    "voiced_ratio",
]
