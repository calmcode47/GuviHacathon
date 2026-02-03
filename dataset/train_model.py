import os
import json
import argparse
import logging
import csv
from pathlib import Path
import numpy as np
from tqdm import tqdm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score
from app.core.features import FEATURE_NAMES
from app.utils.audio import read_mp3_to_pcm_result
from app.services.detector import extract_features_pcm


def read_metadata(meta_csv: str):
    rows = []
    if os.path.exists(meta_csv):
        with open(meta_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                rows.append(row)
    return rows


def collect_samples(base_dir: str, languages):
    seen_paths = set()
    items = []
    # Include real human recordings first (data/human/real/) so they are used when capping per class
    real_dir = os.path.join(base_dir, "human", "real")
    if os.path.isdir(real_dir):
        for fn in sorted(os.listdir(real_dir)):
            if fn.lower().endswith(".mp3"):
                path = os.path.normpath(os.path.join(real_dir, fn))
                seen_paths.add(path)
                items.append((path, 0))  # human
    meta = read_metadata(os.path.join(base_dir, "metadata.csv"))
    for row in meta:
        lang = row.get("language", "").lower()
        if lang not in languages:
            continue
        src = row.get("source_type", "")
        path = row.get("file_path", "")
        if not os.path.isfile(path):
            path2 = os.path.join(base_dir, src, lang, os.path.basename(path))
            if os.path.isfile(path2):
                path = path2
        if not os.path.isfile(path):
            continue
        path = os.path.normpath(path)
        if path in seen_paths:
            continue
        seen_paths.add(path)
        label = 1 if src == "ai" else 0
        items.append((path, label))
    return items


def features_for_path(path: str):
    pcm = read_mp3_to_pcm_result(path)
    feats = extract_features_pcm(pcm)
    v = [float(feats.get(k, 0.0)) for k in FEATURE_NAMES]
    return np.array(v, dtype=np.float32)


def train(X, y):
    mu = np.mean(X, axis=0)
    sigma = np.std(X, axis=0)
    sigma = np.where(sigma < 1e-8, 1.0, sigma)
    Z = (X - mu) / sigma
    clf = LogisticRegression(max_iter=1000, class_weight="balanced")
    clf.fit(Z, y)
    w = clf.coef_[0].astype(np.float32)
    b = float(clf.intercept_[0])
    return mu.astype(np.float32), sigma.astype(np.float32), w, b


def evaluate(mu, sigma, w, b, X, y):
    Z = (X - mu) / sigma
    margin = Z.dot(w) + b
    p = 1.0 / (1.0 + np.exp(-margin))
    auc = roc_auc_score(y, p)
    acc = accuracy_score(y, (p >= 0.5).astype(int))
    return float(auc), float(acc)


def save_model(path: str, mu, sigma, w, b):
    obj = {
        "feature_names": FEATURE_NAMES,
        "mu": mu.tolist(),
        "sigma": sigma.tolist(),
        "weights": w.tolist(),
        "bias": float(b),
        "calib_a": 1.0,
        "calib_b": 0.0,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f)


def main():
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--base-dir", default=str(root / "data"))
    parser.add_argument("--output", default=str(root / "app" / "model" / "model.json"))
    parser.add_argument("--val-split", type=float, default=0.15)
    parser.add_argument("--test-split", type=float, default=0.15)
    parser.add_argument("--languages", nargs="*", default=["tamil", "english", "hindi", "malayalam", "telugu"])
    parser.add_argument("--max-per-class", type=int, default=None, help="Cap samples per class for quick training (default: use all)")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    items = collect_samples(args.base_dir, args.languages)
    if args.max_per_class is not None:
        from collections import defaultdict
        by_label = defaultdict(list)
        for p, l in items:
            by_label[l].append((p, l))
        items = []
        for label in sorted(by_label.keys()):
            items.extend(by_label[label][: args.max_per_class])
        logging.info("Using %d samples (max %d per class)", len(items), args.max_per_class)
    if len(items) < 20:
        logging.error("Not enough samples found")
        return
    paths = [p for p, _ in items]
    labels = np.array([l for _, l in items], dtype=np.int32)
    feats = []
    pbar = tqdm(paths, desc="Extracting features")
    for p in pbar:
        try:
            f = features_for_path(p)
            feats.append(f)
        except Exception:
            feats.append(np.zeros(len(FEATURE_NAMES), dtype=np.float32))
    X = np.vstack(feats)
    classes = np.unique(labels)
    if classes.size < 2:
        logging.error("Dataset contains only one class; add human and ai samples before training")
        return
    try:
        X_train, X_tmp, y_train, y_tmp = train_test_split(X, labels, test_size=(args.val_split + args.test_split), stratify=labels, random_state=42)
        val_ratio = args.val_split / (args.val_split + args.test_split) if (args.val_split + args.test_split) > 0 else 0.5
        X_val, X_test, y_val, y_test = train_test_split(X_tmp, y_tmp, test_size=(1.0 - val_ratio), stratify=y_tmp, random_state=42)
    except ValueError:
        # Fallback: ensure at least one sample per class in training
        idx0 = np.where(labels == 0)[0]
        idx1 = np.where(labels == 1)[0]
        n_train0 = max(1, int(round(len(idx0) * (1.0 - args.val_split - args.test_split))))
        n_train1 = max(1, int(round(len(idx1) * (1.0 - args.val_split - args.test_split))))
        tr_idx = np.concatenate([idx0[:n_train0], idx1[:n_train1]])
        te_idx = np.setdiff1d(np.arange(len(labels)), tr_idx)
        X_train, y_train = X[tr_idx], labels[tr_idx]
        X_tmp, y_tmp = X[te_idx], labels[te_idx]
        split_point = int(round(len(y_tmp) * (args.val_split / max(1e-6, (args.val_split + args.test_split)))))
        X_val, y_val = X_tmp[:split_point], y_tmp[:split_point]
        X_test, y_test = X_tmp[split_point:], y_tmp[split_point:]
    mu, sigma, w, b = train(X_train, y_train)
    auc_val, acc_val = evaluate(mu, sigma, w, b, X_val, y_val)
    auc_test, acc_test = evaluate(mu, sigma, w, b, X_test, y_test)
    logging.info("Validation AUC %.3f Acc %.3f", auc_val, acc_val)
    logging.info("Test AUC %.3f Acc %.3f", auc_test, acc_test)
    save_model(args.output, mu, sigma, w, b)
    logging.info("Model saved to %s", args.output)


if __name__ == "__main__":
    main()
