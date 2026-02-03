import os
import argparse
import logging
import json
from pathlib import Path
import numpy as np
from typing import Dict
from tqdm import tqdm
from joblib import load
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from .data_loader import VoiceDataset, FEATURE_NAMES


def ece(y_true: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(p, bins) - 1
    e = 0.0
    for b in range(n_bins):
        m = idx == b
        if np.sum(m) == 0:
            continue
        conf = float(np.mean(p[m]))
        acc = float(np.mean((p[m] >= 0.5).astype(int) == y_true[m]))
        e += (np.sum(m) / len(p)) * abs(acc - conf)
    return float(e)


def predict(weights: Dict, X: np.ndarray) -> np.ndarray:
    mu = np.array(weights["mu"], dtype=np.float32)
    sigma = np.array(weights["sigma"], dtype=np.float32)
    w = np.array(weights["weights"], dtype=np.float32)
    b = float(weights["bias"])
    a = float(weights.get("calib_a", 1.0))
    c = float(weights.get("calib_b", 0.0))
    Z = (X - mu) / sigma
    m = Z.dot(w) + b
    p = 1.0 / (1.0 + np.exp(-(a * m + c)))
    return p


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--data-dir", default=str(root / "data"))
    parser.add_argument("--weights", default=str(root / "training_out" / "weights.pkl"))
    parser.add_argument("--random-seed", type=int, default=42)
    parser.add_argument("--val-split", type=float, default=0.2)
    parser.add_argument("--output-dir", default=str(root / "evaluation_out"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ds = VoiceDataset(args.data_dir)
    X, y, langs = ds.load(refresh_cache=False)
    weights = load(args.weights)
    from sklearn.model_selection import train_test_split
    _, X_test, _, y_test, _, l_test = train_test_split(X, y, langs, test_size=0.2, stratify=y, random_state=args.random_seed)
    p = predict(weights, X_test)
    y_pred = (p >= 0.5).astype(int)
    acc = float(accuracy_score(y_test, y_pred))
    prec, rec, f1, _ = precision_recall_fscore_support(y_test, y_pred, average="binary")
    auc = float(roc_auc_score(y_test, p))
    cm = confusion_matrix(y_test, y_pred)
    cal_ece = ece(y_test, p, n_bins=10)
    os.makedirs(args.output_dir, exist_ok=True)
    with open(os.path.join(args.output_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump({"accuracy": acc, "precision": float(prec), "recall": float(rec), "f1": float(f1), "roc_auc": auc, "ece": float(cal_ece)}, f)
    plt.figure(figsize=(6, 5))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion Matrix")
    plt.colorbar()
    plt.savefig(os.path.join(args.output_dir, "confusion_matrix.pdf"))
    from sklearn.metrics import RocCurveDisplay
    RocCurveDisplay.from_predictions(y_test, p)
    plt.savefig(os.path.join(args.output_dir, "roc_curve.pdf"))
    bins = np.linspace(0, 1, 11)
    idx = np.digitize(p, bins) - 1
    confs = []
    accs = []
    xs = []
    for b in range(10):
        m = idx == b
        if np.sum(m) == 0:
            continue
        confs.append(np.mean(p[m]))
        accs.append(np.mean((p[m] >= 0.5).astype(int) == y_test[m]))
        xs.append((bins[b] + bins[b + 1]) / 2.0)
    plt.figure(figsize=(6, 5))
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.scatter(confs, accs)
    plt.xlabel("Confidence")
    plt.ylabel("Accuracy")
    plt.title("Calibration")
    plt.savefig(os.path.join(args.output_dir, "calibration.pdf"))
    w = np.array(weights["weights"], dtype=np.float32)
    imp = np.abs(w)
    order = np.argsort(-imp)
    plt.figure(figsize=(8, 5))
    plt.bar([FEATURE_NAMES[i] for i in order], imp[order])
    plt.xticks(rotation=45, ha="right")
    plt.title("Feature Importance")
    plt.tight_layout()
    plt.savefig(os.path.join(args.output_dir, "feature_importance.pdf"))


if __name__ == "__main__":
    main()
