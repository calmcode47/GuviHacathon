import os
import argparse
import json
import numpy as np
from joblib import dump
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from dataset.data_loader import VoiceDataset, FEATURE_NAMES


def fit_platt(margins: np.ndarray, y: np.ndarray) -> dict:
    from sklearn.linear_model import LogisticRegression as LR
    clf = LR(max_iter=1000)
    clf.fit(margins.reshape(-1, 1), y)
    return {"a": float(clf.coef_[0][0]), "b": float(clf.intercept_[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default="data")
    ap.add_argument("--language", default="english")
    ap.add_argument("--output", default="app/model/model.json")
    ap.add_argument("--val-split", type=float, default=0.2)
    ap.add_argument("--random-seed", type=int, default=42)
    args = ap.parse_args()
    ds = VoiceDataset(args.base_dir, languages=[args.language.lower()])
    X, y, langs = ds.load(refresh_cache=False)
    X_train, X_val, y_train, y_val, l_train, l_val = train_test_split(X, y, langs, test_size=args.val_split, stratify=y, random_state=args.random_seED if hasattr(args, 'random_seED') else args.random_seed)
    scaler = StandardScaler()
    Z_train = scaler.fit_transform(X_train)
    Z_val = scaler.transform(X_val)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=args.random_seed)
    base = LogisticRegression(max_iter=1000, solver="lbfgs", class_weight="balanced")
    grid = GridSearchCV(base, {"C": [0.01, 0.1, 1.0, 10.0]}, cv=cv, scoring="roc_auc", n_jobs=1)
    grid.fit(Z_train, y_train)
    best = grid.best_estimator_
    best.fit(Z_train, y_train)
    w = best.coef_[0].astype(np.float32)
    b = float(best.intercept_[0])
    margins_cv = []
    y_cv = []
    for tr_idx, va_idx in cv.split(Z_train, y_train):
        Z_tr, Z_va = Z_train[tr_idx], Z_train[va_idx]
        y_tr, y_va = y_train[tr_idx], y_train[va_idx]
        m = LogisticRegression(max_iter=1000, solver="lbfgs", class_weight="balanced", C=grid.best_params_["C"])
        m.fit(Z_tr, y_tr)
        margins_cv.append(Z_va.dot(m.coef_[0]) + float(m.intercept_[0]))
        y_cv.append(y_va)
    margins_cv = np.concatenate(margins_cv, axis=0)
    y_cv = np.concatenate(y_cv, axis=0)
    calib = fit_platt(margins_cv, y_cv)
    margins_val = Z_val.dot(w) + b
    p_val = 1.0 / (1.0 + np.exp(-(calib["a"] * margins_val + calib["b"])))
    y_pred = (p_val >= 0.5).astype(int)
    acc = float(accuracy_score(y_val, y_pred))
    auc = float(roc_auc_score(y_val, p_val))
    cm = confusion_matrix(y_val, y_pred).tolist()
    os.makedirs("training_out", exist_ok=True)
    weights = {"feature_names": FEATURE_NAMES, "mu": scaler.mean_.astype(np.float32), "sigma": scaler.scale_.astype(np.float32), "weights": w, "bias": b, "calib_a": float(8.0), "calib_b": float(calib["b"])}
    dump(weights, os.path.join("training_out", "weights.pkl"))
    obj = {"feature_names": FEATURE_NAMES, "mean": weights["mu"].tolist(), "std": weights["sigma"].tolist(), "mu": weights["mu"].tolist(), "sigma": weights["sigma"].tolist(), "weights": weights["weights"].tolist(), "bias": weights["bias"], "calib_a": 8.0, "calib_c": float(calib["b"])}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    report = {"accuracy": acc, "roc_auc": auc, "confusion_matrix": cm}
    with open(os.path.join("training_out", "english_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)
    print("OK")


if __name__ == "__main__":
    main()
