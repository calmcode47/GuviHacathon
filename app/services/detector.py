from typing import Dict, Tuple

import numpy as np
import librosa

# Heuristic classifier based on audio features


def _safe_std(vec: np.ndarray) -> float:
    vec = vec[np.isfinite(vec)]
    if vec.size == 0:
        return 0.0
    return float(np.std(vec))


def _safe_mean(vec: np.ndarray) -> float:
    vec = vec[np.isfinite(vec)]
    if vec.size == 0:
        return 0.0
    return float(np.mean(vec))


def extract_features(y: np.ndarray, sr: int) -> Dict[str, float]:
    # Pitch using YIN (robust for monophonic speech)
    f0 = librosa.yin(y, fmin=50, fmax=500, sr=sr)
    pitch_var = _safe_std(f0)

    # Jitter proxy: normalized successive f0 diff
    f0_clean = f0[np.isfinite(f0)]
    if f0_clean.size > 5:
        f0_diff = np.abs(np.diff(f0_clean))
        jitter_proxy = float(np.median(f0_diff) / (np.median(f0_clean) + 1e-8))
    else:
        jitter_proxy = 0.0

    # Energy dynamics
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    energy_var = _safe_std(rms)
    energy_mean = _safe_mean(rms)

    # Spectral features
    flatness = librosa.feature.spectral_flatness(y=y, n_fft=2048, hop_length=512)[0]
    flatness_mean = _safe_mean(flatness)

    # MFCC stability
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
    # Variance over time for each coefficient, then take mean
    mfcc_var_time = np.var(mfcc, axis=1)
    mfcc_var_mean = float(np.mean(mfcc_var_time))

    # Harmonic-percussive separation; ratio approximates HNR
    y_h, y_p = librosa.effects.hpss(y)
    h_energy = float(np.sum(y_h ** 2))
    total_energy = float(np.sum(y ** 2)) + 1e-8
    hnr_ratio = h_energy / total_energy

    # Onset rate (prosodic dynamics)
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    onset_rate = float(np.mean(onset_env))

    return {
        "pitch_var": pitch_var,
        "jitter_proxy": jitter_proxy,
        "energy_var": energy_var,
        "energy_mean": energy_mean,
        "flatness_mean": flatness_mean,
        "mfcc_var_mean": mfcc_var_mean,
        "hnr_ratio": hnr_ratio,
        "onset_rate": onset_rate,
    }


def classify(features: Dict[str, float]) -> Tuple[str, float, str]:
    """
    Combine features into an AI-likeness score and classify.

    Returns: (classification, confidence, explanation)
    """
    # Normalize features to roughly comparable ranges
    # These ranges are heuristic and may be tuned.
    pitch_var_norm = np.clip(features["pitch_var"] / 30.0, 0.0, 1.0)     # human tends to be higher
    jitter_norm = np.clip(features["jitter_proxy"] / 0.05, 0.0, 1.0)     # human tends to be higher
    energy_var_norm = np.clip(features["energy_var"] / 0.05, 0.0, 1.0)   # human tends to be higher
    mfcc_var_norm = np.clip(features["mfcc_var_mean"] / 100.0, 0.0, 1.0) # human tends to be higher
    flatness_norm = np.clip(features["flatness_mean"] / 0.5, 0.0, 1.0)   # noise-like; AI speech tends to be lower
    hnr_norm = np.clip(features["hnr_ratio"], 0.0, 1.0)                   # AI speech tends to be higher (cleaner)

    # AI-likeness increases when variability is LOW and HNR is HIGH
    ai_score = (
        (1.0 - pitch_var_norm) * 0.22 +
        (1.0 - jitter_norm) * 0.22 +
        (1.0 - energy_var_norm) * 0.15 +
        (1.0 - mfcc_var_norm) * 0.18 +
        (1.0 - flatness_norm) * 0.08 +
        (hnr_norm) * 0.15
    )
    ai_score = float(np.clip(ai_score, 0.0, 1.0))

    classification = "AI_GENERATED" if ai_score >= 0.5 else "HUMAN"
    confidence = ai_score if classification == "AI_GENERATED" else (1.0 - ai_score)

    # Build explanation from top drivers
    drivers = []
    if (1.0 - pitch_var_norm) > 0.6:
        drivers.append("Unusually stable pitch")
    if (1.0 - jitter_norm) > 0.6:
        drivers.append("Low micro-variations (jitter)")
    if (1.0 - energy_var_norm) > 0.6:
        drivers.append("Consistent energy dynamics")
    if hnr_norm > 0.6:
        drivers.append("Clean harmonic profile (high HNR)")
    if (1.0 - mfcc_var_norm) > 0.6:
        drivers.append("Stable spectral envelope (MFCCs)")

    if not drivers:
        if classification == "AI_GENERATED":
            drivers.append("Multiple stability cues detected")
        else:
            drivers.append("Natural variability across pitch and energy")

    explanation = ", ".join(drivers)

    return classification, float(np.clip(confidence, 0.0, 1.0)), explanation