from typing import Dict, List, Tuple
import json
import logging
import os
from pathlib import Path
from app.core.config import HIGH_CONFIDENCE_THRESHOLD, BORDERLINE_MIN_CONFIDENCE

import numpy as np

from app.utils.audio import PCMDecodeResult


logger = logging.getLogger(__name__)


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
    if BORDERLINE_MIN_CONFIDENCE <= conf < HIGH_CONFIDENCE_THRESHOLD:
        conf = float(conf)
    return label, conf, p_ai


def get_default_classifier() -> LogisticClassifier:
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        model_path = Path(env_path)
    else:
        model_path = Path(__file__).resolve().parents[1] / "model" / "model.json"
    if model_path.exists():
        try:
            with open(model_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            names = obj["feature_names"]
            mu = np.array(obj["mu"], dtype=np.float32)
            sigma = np.array(obj["sigma"], dtype=np.float32)
            weights = np.array(obj["weights"], dtype=np.float32)
            bias = float(obj["bias"])
            calib_a = float(obj.get("calib_a", 1.0))
            calib_b = float(obj.get("calib_b", 0.0))
            logger.info("Loaded voice classifier model from %s", model_path)
            return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)
        except Exception as exc:
            logger.exception("Failed to load classifier model from %s; falling back to default classifier", model_path)
    else:
        logger.warning("Model file %s not found; using default zero-weight classifier", model_path)
        names = [
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
    mu = np.array([98.29513549804688, 0.015771353617310524, 0.44652023911476135, 0.04289805889129639, 1958.75, 0.023493962362408638, 0.9435814619064331, 0.10025333613157272, 18.008665084838867, 1.0], dtype=np.float32)
    sigma = np.array([26.92410659790039, 0.0039332215674221516, 0.10752879828214645, 0.06266656517982483, 549.4205322265625, 0.002224999712780118, 0.01201669592410326, 0.00019136597984470427, 6.902961730957031, 1.0], dtype=np.float32)
    weights = np.array([0.08873581886291504, -0.11327959597110748, 0.08327771723270416, 0.08136289566755295, -0.08587891608476639, 0.15382376313209534, -0.04701659083366394, 0.014387399889528751, -0.002227391581982374, 0.0], dtype=np.float32)
    bias = 0.0007442798871767299
    calib_a = 3.2714065908313086
    calib_b = -0.0038372466256048152
    return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)



