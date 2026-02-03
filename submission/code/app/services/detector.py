from typing import Dict, Tuple, List

import numpy as np
import librosa
from app.utils.audio import PCMDecodeResult
from app.core.config import TARGET_SAMPLE_RATE

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


def _frame_params(sr: int) -> Tuple[int, int, int]:
    fl = max(1, int(round(sr * 0.032)))
    hl = max(1, int(round(sr * 0.010)))
    n_fft = 1
    while n_fft < fl:
        n_fft <<= 1
    return fl, hl, n_fft


def _circular_resultant(phases: np.ndarray) -> float:
    c = float(np.mean(np.cos(phases)))
    s = float(np.mean(np.sin(phases)))
    r = float(np.sqrt(c * c + s * s))
    return r


def _entropy_norm(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0
    x = np.maximum(x, 0.0)
    s = float(np.sum(x)) + 1e-12
    p = x / s
    h = float(-np.sum(p * np.log(p + 1e-12)))
    h_max = float(np.log(max(1, p.size)))
    return h / (h_max + 1e-12)


def _iqr(x: np.ndarray) -> float:
    x = x[np.isfinite(x)]
    if x.size == 0:
        return 0.0
    q75 = float(np.percentile(x, 75))
    q25 = float(np.percentile(x, 25))
    return q75 - q25


def _pause_lengths(rms: np.ndarray) -> List[int]:
    thr = float(np.percentile(rms, 20))
    mask = rms <= thr
    lengths = []
    count = 0
    for v in mask:
        if v:
            count += 1
        elif count > 0:
            lengths.append(count)
            count = 0
    if count > 0:
        lengths.append(count)
    return lengths


def _per_channel_features(y_ch: np.ndarray, sr: int) -> Dict[str, float]:
    y_f = y_ch.astype(np.float32) / 32768.0
    if sr > TARGET_SAMPLE_RATE:
        y_f = librosa.resample(y_f, orig_sr=sr, target_sr=TARGET_SAMPLE_RATE)
        sr = TARGET_SAMPLE_RATE
    fl, hl, n_fft = _frame_params(sr)
    f0 = librosa.yin(y_f, fmin=62.5, fmax=500, sr=sr, frame_length=fl, hop_length=hl)
    f0_clean = f0[np.isfinite(f0)]
    if f0_clean.size > 5:
        jitter = float(np.median(np.abs(np.diff(f0_clean))) / (np.median(f0_clean) + 1e-8))
    else:
        jitter = 0.0
    pitch_var = float(np.std(f0[np.isfinite(f0)])) if np.any(np.isfinite(f0)) else 0.0
    S = librosa.stft(y=y_f, n_fft=n_fft, hop_length=hl)
    mag = np.abs(S)
    rms = librosa.feature.rms(y=y_f, frame_length=fl, hop_length=hl)[0]
    energy_var = float(np.std(rms))
    flat = librosa.feature.spectral_flatness(S=mag)[0]
    flat_mean = float(np.mean(flat))
    roll = librosa.feature.spectral_rolloff(S=mag, sr=sr, roll_percent=0.85)[0]
    roll_median = float(np.median(roll))
    phi = np.angle(S)
    pc = np.array([_circular_resultant(phi[:, t]) for t in range(phi.shape[1])], dtype=np.float32)
    phase_coh_median = float(np.median(pc))
    y_h, y_p = librosa.effects.hpss(y_f)
    h_energy = float(np.sum(y_h ** 2))
    total_energy = float(np.sum(y_f ** 2)) + 1e-8
    hnr = h_energy / total_energy
    onset_env = librosa.onset.onset_strength(y=y_f, sr=sr, hop_length=hl)
    if onset_env.size > 1:
        d_on = np.abs(np.diff(onset_env))
        thr = float(np.percentile(d_on, 90))
        temporal_rate = float(np.mean(d_on > thr))
    else:
        temporal_rate = 0.0
    ent = _entropy_norm(rms)
    pauses = _pause_lengths(rms)
    pause_std = float(np.std(pauses)) if len(pauses) > 0 else 0.0
    voiced_ratio = float(f0_clean.size) / float(f0.size + 1e-8)
    return {
        "pitch_var": pitch_var,
        "jitter_proxy": jitter,
        "hnr_ratio": hnr,
        "spectral_flatness_mean": flat_mean,
        "spectral_rolloff_median": roll_median,
        "phase_coherence_median": phase_coh_median,
        "energy_entropy_norm": ent,
        "temporal_discontinuity_rate": temporal_rate,
        "prosody_pause_std": pause_std,
        "prosody_f0_var_median": pitch_var,
        "voiced_ratio": voiced_ratio,
    }


def extract_features_pcm(pcm: PCMDecodeResult) -> Dict[str, float]:
    sr = pcm.sample_rate
    ch = pcm.channels
    feats = []
    for ci in range(ch):
        y_ch = pcm.waveform_int16[ci]
        feats.append(_per_channel_features(y_ch, sr))
    keys = list(feats[0].keys()) if feats else []
    agg = {}
    for k in keys:
        vals = np.array([f[k] for f in feats], dtype=np.float32)
        agg[k] = float(np.median(vals))
        agg[k + "_iqr"] = float(_iqr(vals))
        agg[k + "_p05"] = float(np.percentile(vals, 5))
        agg[k + "_p95"] = float(np.percentile(vals, 95))
    return agg
