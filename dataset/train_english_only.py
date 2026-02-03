import os
import argparse
import json
import numpy as np
from joblib import dump
from sklearn.model_selection import train_test_split, StratifiedKFold, GridSearchCV
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, roc_auc_score, confusion_matrix
from .data_loader import VoiceDataset, FEATURE_NAMES


def fit_platt(margins: np.ndarray, y: np.ndarray) -> dict:
    from sklearn.linear_model import LogisticRegression as LR
    clf = LR(max_iter=1000)
    clf.fit(margins.reshape(-1, 1), y)
    return {"a": float(clf.coef_[0][0]), "b": float(clf.intercept_[0])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--output-dir", default="training_out")
    ap.add_argument("--val-split", type=float, default=0.2)
    ap.add_argument("--random-seed", type=int, default=42)
    args = ap.parse_args()
    ds = VoiceDataset(args.data_dir, languages=["english"])
    X, y, langs = ds.load(refresh_cache=False)
    X_train, X_val, y_train, y_val, l_train, l_val = train_test_split(X, y, langs, test_size=args.val_split, stratify=y, random_state=args.random_seed)
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
    os.makedirs(args.output_dir, exist_ok=True)
    report = {"accuracy": acc, "roc_auc": auc, "confusion_matrix": cm, "feature_names": FEATURE_NAMES, "best_C": float(grid.best_params_["C"])}
    with open(os.path.join(args.output_dir, "report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f)
    weights = {"feature_names": FEATURE_NAMES, "mu": scaler.mean_.astype(np.float32), "sigma": scaler.scale_.astype(np.float32), "weights": w, "bias": b, "calib_a": float(8.0), "calib_b": float(calib["b"])}
    dump(weights, os.path.join(args.output_dir, "weights.pkl"))
    print("OK")


if __name__ == "__main__":
    main()
