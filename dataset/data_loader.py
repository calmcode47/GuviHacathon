import os
import argparse
import logging
import json
from typing import List, Tuple, Dict, Optional
import numpy as np
from tqdm import tqdm
from sklearn.model_selection import train_test_split
from app.utils.audio import read_mp3_to_pcm_result
from app.services.detector import extract_features_pcm

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


class VoiceDataset:
    def __init__(self, data_dir: str, languages: Optional[List[str]] = None, cache_dir: Optional[str] = None) -> None:
        self.data_dir = data_dir
        self.languages = languages
        self.cache_dir = cache_dir or os.path.join(data_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.paths: List[str] = []
        self.labels: List[int] = []
        self.langs: List[str] = []

    def scan(self) -> None:
        self.paths = []
        self.labels = []
        self.langs = []
        for source, label in [("human", 0), ("ai", 1)]:
            base = os.path.join(self.data_dir, source)
            if not os.path.isdir(base):
                continue
            for lang in sorted(os.listdir(base)):
                if self.languages and lang.lower() not in self.languages:
                    continue
                d = os.path.join(base, lang)
                if not os.path.isdir(d):
                    continue
                for root, _, files in os.walk(d):
                    for fn in files:
                        if fn.lower().endswith(".mp3"):
                            self.paths.append(os.path.join(root, fn))
                            self.labels.append(label)
                            self.langs.append(lang.lower())

    def _cache_path(self) -> str:
        return os.path.join(self.cache_dir, "features.npz")

    def load(self, refresh_cache: bool = False) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        self.scan()
        cache_path = self._cache_path()
        if os.path.isfile(cache_path) and not refresh_cache:
            data = np.load(cache_path, allow_pickle=True)
            X = data["X"]
            y = data["y"]
            langs = data["langs"]
            return X, y, langs
        feats = []
        for p in tqdm(self.paths, desc="Extracting features"):
            try:
                pcm = read_mp3_to_pcm_result(p)
                fdict = extract_features_pcm(pcm)
                v = [float(fdict.get(k, 0.0)) for k in FEATURE_NAMES]
                feats.append(np.array(v, dtype=np.float32))
            except Exception:
                feats.append(np.zeros(len(FEATURE_NAMES), dtype=np.float32))
        X = np.vstack(feats) if feats else np.zeros((0, len(FEATURE_NAMES)), dtype=np.float32)
        y = np.array(self.labels, dtype=np.int32)
        langs = np.array(self.langs, dtype=np.str_)
        np.savez(cache_path, X=X, y=y, langs=langs)
        return X, y, langs

    def balanced_indices(self, y: np.ndarray, seed: int = 42) -> np.ndarray:
        rng = np.random.default_rng(seed)
        idx0 = np.where(y == 0)[0]
        idx1 = np.where(y == 1)[0]
        n = min(len(idx0), len(idx1))
        if n == 0:
            return np.arange(len(y))
        idx0_s = rng.choice(idx0, n, replace=False)
        idx1_s = rng.choice(idx1, n, replace=False)
        idx = np.concatenate([idx0_s, idx1_s])
        rng.shuffle(idx)
        return idx

    def split(self, X: np.ndarray, y: np.ndarray, langs: np.ndarray, val_split: float, test_split: float, seed: int, balance: bool = False) -> Dict[str, np.ndarray]:
        idx = np.arange(len(y))
        if balance:
            idx = self.balanced_indices(y, seed)
        Xf = X[idx]
        yf = y[idx]
        lf = langs[idx]
        if val_split + test_split > 0.0:
            X_train, X_tmp, y_train, y_tmp, l_train, l_tmp = train_test_split(Xf, yf, lf, test_size=(val_split + test_split), stratify=yf, random_state=seed)
            if test_split <= 1e-8:
                X_val, y_val, l_val = X_tmp, y_tmp, l_tmp
                X_test = np.empty((0, Xf.shape[1]))
                y_test = np.empty((0,), dtype=yf.dtype)
                l_test = np.empty((0,), dtype=l_train.dtype)
            else:
                vs = val_split / (val_split + test_split)
                X_val, X_test, y_val, y_test, l_val, l_test = train_test_split(X_tmp, y_tmp, l_tmp, test_size=(1.0 - vs), stratify=y_tmp, random_state=seed)
        else:
            X_train, y_train, l_train = Xf, yf, lf
            X_val, y_val, l_val = np.empty((0, Xf.shape[1])), np.empty((0,), dtype=yf.dtype), np.empty((0,), dtype=l_train.dtype)
            X_test, y_test, l_test = np.empty((0, Xf.shape[1])), np.empty((0,), dtype=yf.dtype), np.empty((0,), dtype=l_train.dtype)
        return {
            "train_X": X_train,
            "train_y": y_train,
            "train_langs": l_train,
            "val_X": X_val,
            "val_y": y_val,
            "val_langs": l_val,
            "test_X": X_test,
            "test_y": y_test,
            "test_langs": l_test,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default="data")
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--test-split", type=float, default=0.0)
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--balance", action="store_true")
    parser.add_argument("--refresh-cache", action="store_true")
    parser.add_argument("--output-json", default="dataset/splits.json")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ds = VoiceDataset(args.data_dir)
    X, y, langs = ds.load(refresh_cache=args.refresh_cache)
    splits = ds.split(X, y, langs, val_split=args.val_split, test_split=args.test_split, seed=args.random_seed, balance=args.balance)
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)
    obj = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in splits.items()}
    with open(args.output_json, "w", encoding="utf-8") as f:
        json.dump(obj, f)


if __name__ == "__main__":
    main()
