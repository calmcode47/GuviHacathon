import os
import argparse
import logging
import json
from pathlib import Path
import numpy as np
from typing import Dict, List
from tqdm import tqdm
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, GridSearchCV, train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from joblib import dump
from data_loader import VoiceDataset, FEATURE_NAMES


def per_language_accuracy(y_true: np.ndarray, y_pred: np.ndarray, langs: np.ndarray) -> Dict[str, float]:
    d: Dict[str, float] = {}
    for lang in np.unique(langs):
        idx = np.where(langs == lang)[0]
        if idx.size == 0:
            continue
        d[str(lang)] = float(accuracy_score(y_true[idx], y_pred[idx]))
    return d


def fit_platt(margins: np.ndarray, y: np.ndarray) -> Dict[str, float]:
    Xp = margins.reshape(-1, 1)
    clf = LogisticRegression(max_iter=1000)
    clf.fit(Xp, y)
    a = float(clf.coef_[0][0])
    b = float(clf.intercept_[0])
    return {"a": a, "b": b}


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--data-dir", default=str(root / "data"))
    parser.add_argument("--output-dir", default=str(root / "training_out"))
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ds = VoiceDataset(args.data_dir)
    X, y, langs = ds.load(refresh_cache=False)
    if np.unique(y).size < 2:
        logging.error("Need both human and ai samples")
        return
    X_train, X_val, y_train, y_val, l_train, l_val = train_test_split(X, y, langs, test_size=args.val_split, stratify=y, random_state=args.random_seed)
    scaler = StandardScaler()
    Z_train = scaler.fit_transform(X_train)
    Z_val = scaler.transform(X_val)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.random_seed)
    grid = GridSearchCV(LogisticRegression(max_iter=1000, penalty="l2", solver="lbfgs", class_weight="balanced"), {"C": [0.01, 0.1, 1.0, 10.0]}, cv=cv, scoring="roc_auc", n_jobs=1)
    grid.fit(Z_train, y_train)
    best = grid.best_estimator_
    best.fit(Z_train, y_train)
    w = best.coef_[0].astype(np.float32)
    b = float(best.intercept_[0])
    margins_val = Z_val.dot(w) + b
    calib = fit_platt(margins_val, y_val)
    p_val = 1.0 / (1.0 + np.exp(-(calib["a"] * margins_val + calib["b"])))
    y_pred = (p_val >= 0.5).astype(int)
    acc = float(accuracy_score(y_val, y_pred))
    auc = float(roc_auc_score(y_val, p_val))
    cm = confusion_matrix(y_val, y_pred).tolist()
    per_lang = per_language_accuracy(y_val, y_pred, l_val)
    os.makedirs(args.output_dir, exist_ok=True)
    report = {
        "accuracy": acc,
        "roc_auc": auc,
        "per_language_accuracy": per_lang,
        "confusion_matrix": cm,
        "feature_names": FEATURE_NAMES,
        "best_C": float(grid.best_params_["C"]),
    }
    with open(os.path.join(args.output_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)
    weights = {
        "feature_names": FEATURE_NAMES,
        "mu": scaler.mean_.astype(np.float32),
        "sigma": scaler.scale_.astype(np.float32),
        "weights": w,
        "bias": b,
        "calib_a": float(calib["a"]),
        "calib_b": float(calib["b"]),
    }
    dump(weights, os.path.join(args.output_dir, "weights.pkl"))
    logging.info("Saved %s", os.path.join(args.output_dir, "weights.pkl"))


if __name__ == "__main__":
    main()
