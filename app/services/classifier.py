from typing import Dict, List, Tuple
import numpy as np
from app.utils.audio import PCMDecodeResult
import os
import json


class LogisticClassifier:
    def __init__(self, feature_names: List[str], mu: np.ndarray, sigma: np.ndarray, weights: np.ndarray, bias: float, calib_a: float, calib_b: float):
        self.feature_names = feature_names
        self.mu = mu.astype(np.float32)
        self.sigma = np.maximum(sigma.astype(np.float32), 1e-8)
        self.weights = weights.astype(np.float32)
        self.bias = float(bias)
        self.calib_a = float(calib_a)
        self.calib_b = float(calib_b)

    def _vectorize(self, features: Dict[str, float]) -> np.ndarray:
        v = np.array([float(features.get(k, 0.0)) for k in self.feature_names], dtype=np.float32)
        return v

    def _standardize(self, v: np.ndarray) -> np.ndarray:
        return (v - self.mu) / self.sigma

    def _sigmoid(self, x: float) -> float:
        return float(1.0 / (1.0 + np.exp(-x)))

    def predict_proba(self, features: Dict[str, float]) -> float:
        v = self._vectorize(features)
        z = self._standardize(v)
        margin = float(np.dot(self.weights, z) + self.bias)
        p = self._sigmoid(self.calib_a * margin + self.calib_b)
        return p


def compute_reliability(pcm: PCMDecodeResult) -> float:
    r = 1.0
    if pcm.short_audio:
        r *= 0.6
    if pcm.sample_rate_suspect:
        r *= 0.85
    if not pcm.format_valid:
        r *= 0.9
    return float(np.clip(r, 0.0, 1.0))


def classify_features(features: Dict[str, float], pcm: PCMDecodeResult, model: LogisticClassifier) -> Tuple[str, float, float]:
    p_ai = model.predict_proba(features)
    label = "AI_GENERATED" if p_ai >= 0.5 else "HUMAN"
    base_conf = p_ai if label == "AI_GENERATED" else (1.0 - p_ai)
    r = compute_reliability(pcm)
    conf = float(np.clip(r * base_conf, 0.0, 1.0))
    return label, conf, p_ai


def get_default_classifier() -> LogisticClassifier:
    path = os.getenv("MODEL_PATH", "app/model/model.json")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            names = obj["feature_names"]
            mu = np.array(obj["mu"], dtype=np.float32)
            sigma = np.array(obj["sigma"], dtype=np.float32)
            weights = np.array(obj["weights"], dtype=np.float32)
            bias = float(obj["bias"])
            calib_a = float(obj.get("calib_a", 1.0))
            calib_b = float(obj.get("calib_b", 0.0))
            return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)
        except Exception:
            pass
    names = [
        "pitch_var",
        "jitter_proxy",
        "hnr_ratio",
        "spectral_flatness_mean",
        "phase_coherence_median",
        "energy_entropy_norm",
        "temporal_discontinuity_rate",
        "prosody_pause_std",
        "voiced_ratio",
    ]
    mu = np.array([
        20.0,
        0.03,
        0.5,
        0.2,
        0.6,
        0.7,
        0.1,
        5.0,
        0.6,
    ], dtype=np.float32)
    sigma = np.array([
        15.0,
        0.02,
        0.2,
        0.1,
        0.2,
        0.2,
        0.1,
        3.0,
        0.2,
    ], dtype=np.float32)
    weights = np.array([
        -0.9,
        -0.8,
        0.7,
        -0.4,
        0.6,
        -0.5,
        -0.2,
        -0.5,
        0.2,
    ], dtype=np.float32)
    bias = 0.0
    calib_a = 1.0
    calib_b = 0.0
    return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)
