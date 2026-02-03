import os
import argparse
import json
import time
import numpy as np
from typing import Dict
from tqdm import tqdm
from joblib import load
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score, confusion_matrix, RocCurveDisplay
from sklearn.model_selection import train_test_split
from dataset.data_loader import VoiceDataset, FEATURE_NAMES
from app.services.classifier import LogisticClassifier


def load_model_args(model_path: str) -> Dict:
    if model_path and os.path.isfile(model_path):
        with open(model_path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        names = obj.get("feature_names", FEATURE_NAMES)
        mu = np.array(obj["mu"], dtype=np.float32)
        sigma = np.array(obj["std"] if "std" in obj else obj["sigma"], dtype=np.float32)
        weights = np.array(obj["weights"], dtype=np.float32)
        bias = float(obj["bias"])
        a = float(obj.get("calib_a", obj.get("calib_c", 1.0)))
        b = float(obj.get("calib_b", 0.0))
        return {"feature_names": names, "mu": mu, "sigma": sigma, "weights": weights, "bias": bias, "calib_a": a, "calib_b": b}
    pkl = "training_out/weights.pkl"
    w = load(pkl)
    return {"feature_names": w["feature_names"], "mu": np.array(w["mu"], dtype=np.float32), "sigma": np.array(w["sigma"], dtype=np.float32), "weights": np.array(w["weights"], dtype=np.float32), "bias": float(w["bias"]), "calib_a": float(w.get("calib_a", 1.0)), "calib_b": float(w.get("calib_b", 0.0))}


def predict_probs(model: LogisticClassifier, X: np.ndarray, names: list) -> np.ndarray:
    mu = model.mu
    sigma = model.sigma
    w = model.weights
    b = model.bias
    a = model.calib_a
    c = model.calib_b
    Z = (X - mu) / sigma
    m = Z.dot(w) + b
    p = 1.0 / (1.0 + np.exp(-(a * m + c)))
    return p


def per_language_accuracy(y_true: np.ndarray, y_pred: np.ndarray, langs: np.ndarray) -> Dict[str, float]:
    d = {}
    for lang in np.unique(langs):
        idx = np.where(langs == lang)[0]
        if idx.size == 0:
            continue
        d[str(lang)] = float(accuracy_score(y_true[idx], y_pred[idx]))
    return d


def ece_binary(y_true: np.ndarray, p: np.ndarray, n_bins: int = 10) -> float:
    pred = (p >= 0.5).astype(int)
    conf = np.maximum(p, 1.0 - p)
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    idx = np.digitize(conf, bins) - 1
    e = 0.0
    for b in range(n_bins):
        m = idx == b
        if np.sum(m) == 0:
            continue
        c = float(np.mean(conf[m]))
        acc = float(np.mean(pred[m] == y_true[m]))
        e += (np.sum(m) / len(p)) * abs(acc - c)
    return float(e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="app/model/model.json")
    ap.add_argument("--test-dir", default="data")
    ap.add_argument("--output-dir", default="results")
    ap.add_argument("--val-split", type=float, default=0.2)
    ap.add_argument("--random-seed", type=int, default=42)
    args = ap.parse_args()
    os.makedirs(args.output_dir, exist_ok=True)
    ds = VoiceDataset(args.test_dir)
    X, y, langs = ds.load(refresh_cache=False)
    X_train, X_tmp, y_train, y_tmp, l_train, l_tmp = train_test_split(X, y, langs, test_size=args.val_split, stratify=y, random_state=args.random_seed)
    X_val, X_test, y_val, y_test, l_val, l_test = train_test_split(X_tmp, y_tmp, l_tmp, test_size=0.5, stratify=y_tmp, random_state=args.random_seed)
    margs = load_model_args(args.model)
    model = LogisticClassifier(margs["feature_names"], margs["mu"], margs["sigma"], margs["weights"], margs["bias"], margs["calib_a"], margs["calib_b"])
    t0 = time.perf_counter()
    p_train = predict_probs(model, X_train, margs["feature_names"])
    p_val = predict_probs(model, X_val, margs["feature_names"])
    p_test = predict_probs(model, X_test, margs["feature_names"])
    t1 = time.perf_counter()
    yhat_train = (p_train >= 0.5).astype(int)
    yhat_val = (p_val >= 0.5).astype(int)
    yhat_test = (p_test >= 0.5).astype(int)
    acc_train = float(accuracy_score(y_train, yhat_train))
    acc_val = float(accuracy_score(y_val, yhat_val))
    acc_test = float(accuracy_score(y_test, yhat_test))
    prec_ai, rec_ai, f1_ai, _ = precision_recall_fscore_support(y_test, yhat_test, average="binary")
    auc_test = float(roc_auc_score(y_test, p_test))
    ece_test = float(ece_binary(y_test, p_test, n_bins=10))
    cm_test = confusion_matrix(y_test, yhat_test)
    per_lang = per_language_accuracy(y_test, yhat_test, l_test)
    report = {
        "accuracy_train": acc_train,
        "accuracy_val": acc_val,
        "accuracy_test": acc_test,
        "roc_auc_test": auc_test,
        "ece_test": ece_test,
        "per_language_accuracy_test": per_lang,
        "precision_ai": float(prec_ai),
        "recall_ai": float(rec_ai),
        "f1_ai": float(f1_ai),
        "confusion_matrix_test": cm_test.tolist(),
        "feature_importance": np.abs(margs["weights"]).tolist(),
        "feature_names": margs["feature_names"],
        "train_time_sec": float(t1 - t0),
        "samples": {"train": int(len(y_train)), "val": int(len(y_val)), "test": int(len(y_test))},
        "timestamp": int(time.time()),
    }
    with open(os.path.join(args.output_dir, "training_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)
    plt.figure(figsize=(6, 5))
    sns.heatmap(cm_test, annot=True, fmt="d", cmap="Blues")
    plt.title("Confusion Matrix (Test)")
    plt.savefig(os.path.join(args.output_dir, "cm_test.png"))
    RocCurveDisplay.from_predictions(y_test, p_test)
    plt.savefig(os.path.join(args.output_dir, "roc_test.png"))
    bins = np.linspace(0, 1, 11)
    idx = np.digitize(np.maximum(p_test, 1.0 - p_test), bins) - 1
    xs = []
    confs = []
    accs = []
    for b in range(10):
        m = idx == b
        if np.sum(m) == 0:
            continue
        xs.append((bins[b] + bins[b + 1]) / 2.0)
        confs.append(float(np.mean(np.maximum(p_test[m], 1.0 - p_test[m]))))
        accs.append(float(np.mean(((p_test[m] >= 0.5).astype(int)) == y_test[m])))
    plt.figure(figsize=(6, 5))
    plt.plot([0, 1], [0, 1], "--", color="gray")
    plt.scatter(confs, accs)
    plt.title("Calibration (Test)")
    plt.xlabel("Confidence")
    plt.ylabel("Accuracy")
    plt.savefig(os.path.join(args.output_dir, "calibration_test.png"))
    imp = np.abs(margs["weights"])
    order = np.argsort(-imp)
    plt.figure(figsize=(8, 5))
    plt.bar([margs["feature_names"][i] for i in order], imp[order])
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.title("Feature Importance")
    plt.savefig(os.path.join(args.output_dir, "feature_importance.png"))


if __name__ == "__main__":
    main()
