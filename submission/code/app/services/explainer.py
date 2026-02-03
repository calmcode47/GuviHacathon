from typing import Dict
import numpy as np
from app.services.classifier import LogisticClassifier


AI_PHRASES = {
    "pitch_var": "Unnatural pitch stability detected",
    "jitter_proxy": "Low micro-jitter typical of synthetic speech",
    "hnr_ratio": "Clean harmonic profile typical of synthesis",
    "spectral_flatness_mean": "Stable spectral envelope across frames",
    "phase_coherence_median": "High phase coherence across frames",
    "energy_entropy_norm": "Uniform energy envelope with low entropy",
    "temporal_discontinuity_rate": "Abrupt temporal transitions detected",
    "prosody_pause_std": "Uniform pause timing",
    "voiced_ratio": "Extended voiced continuity",
}


HUMAN_PHRASES = {
    "pitch_var": "Natural pitch variability observed",
    "jitter_proxy": "Micro-jitter consistent with human phonation",
    "hnr_ratio": "Variable harmonic-to-noise profile",
    "spectral_flatness_mean": "Fluctuating spectral texture",
    "phase_coherence_median": "Irregular phase relationships",
    "energy_entropy_norm": "Dynamic energy envelope",
    "temporal_discontinuity_rate": "Natural temporal variability",
    "prosody_pause_std": "Variable pause timing",
    "voiced_ratio": "Balanced voiced and unvoiced distribution",
}


def _standardize(model: LogisticClassifier, features: Dict[str, float]) -> np.ndarray:
    v = np.array([float(features.get(k, 0.0)) for k in model.feature_names], dtype=np.float32)
    z = (v - model.mu) / model.sigma
    return z


def explain(features: Dict[str, float], model: LogisticClassifier, label: str) -> str:
    z = _standardize(model, features)
    contrib = model.weights * z
    idxs = np.argsort(-np.abs(contrib))
    phrases = []
    for idx in idxs:
        name = model.feature_names[idx]
        val = contrib[idx]
        if label == "AI_GENERATED" and val > 0:
            msg = AI_PHRASES.get(name)
            if msg:
                phrases.append(msg)
        elif label == "HUMAN" and val < 0:
            msg = HUMAN_PHRASES.get(name)
            if msg:
                phrases.append(msg)
        if len(phrases) >= 2:
            break
    if not phrases:
        if label == "AI_GENERATED":
            phrases = ["Synthesis-like stability across key cues"]
        else:
            phrases = ["Human-like variability across key cues"]
    return "; ".join(phrases)
