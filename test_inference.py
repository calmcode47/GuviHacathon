import os
import argparse
import json
import time
import base64
import numpy as np
from typing import Dict, List, Tuple
from app.services.classifier import LogisticClassifier
from app.services.detector import extract_features_pcm
from app.utils.audio import read_mp3_to_pcm_result
from joblib import load


def load_weights() -> Dict:
    w = load("training_out/weights.pkl")
    return {"feature_names": w["feature_names"], "mu": np.array(w["mu"], dtype=np.float32), "sigma": np.array(w["sigma"], dtype=np.float32), "weights": np.array(w["weights"], dtype=np.float32), "bias": float(w["bias"]), "calib_a": float(w.get("calib_a", 1.0)), "calib_b": float(w.get("calib_b", 0.0))}


def select_samples(base_dir: str, per_lang_per_class: int = 5) -> List[Tuple[str, str]]:
    items = []
    for cls in ["human", "ai"]:
        cdir = os.path.join(base_dir, cls)
        if not os.path.isdir(cdir):
            continue
        for lang in sorted(os.listdir(cdir)):
            ldir = os.path.join(cdir, lang)
            if not os.path.isdir(ldir):
                continue
            files = [os.path.join(ldir, f) for f in os.listdir(ldir) if f.lower().endswith(".mp3")]
            files = sorted(files)[:per_lang_per_class]
            for f in files:
                items.append((cls, f))
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--test-dir", default="data")
    ap.add_argument("--output", default="results/test_results.json")
    ap.add_argument("--per-lang-per-class", type=int, default=5)
    args = ap.parse_args()
    w = load_weights()
    clf = LogisticClassifier(w["feature_names"], w["mu"], w["sigma"], w["weights"], w["bias"], w["calib_a"], w["calib_b"])
    items = select_samples(args.test_dir, args.per_lang_per_class)
    recs = []
    t0 = time.perf_counter()
    for cls, path in items:
        t_s = time.perf_counter()
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        t_d = time.perf_counter()
        pcm = read_mp3_to_pcm_result(path)
        t_dec = time.perf_counter()
        feats = extract_features_pcm(pcm)
        t_feat = time.perf_counter()
        p = clf.predict_proba(feats)
        label = "AI_GENERATED" if p >= 0.5 else "HUMAN"
        conf = p if label == "AI_GENERATED" else (1.0 - p)
        t_pred = time.perf_counter()
        recs.append({"true_class": cls, "path": path.replace("\\", "/"), "pred_label": label, "confidence": float(conf), "p_ai": float(p), "latency_decode_b64_ms": float((t_d - t_s) * 1000.0), "latency_decode_pcm_ms": float((t_dec - t_d) * 1000.0), "latency_features_ms": float((t_feat - t_dec) * 1000.0), "latency_classify_ms": float((t_pred - t_feat) * 1000.0), "latency_total_ms": float((t_pred - t_s) * 1000.0)})
    t1 = time.perf_counter()
    preds = [1 if r["pred_label"] == "AI_GENERATED" else 0 for r in recs]
    truth = [0 if r["true_class"] == "human" else 1 for r in recs]
    langs = []
    for r in recs:
        parts = r["path"].split("/")
        idx = parts.index("data")
        langs.append(parts[idx + 3] if len(parts) > idx + 3 else "unknown")
    acc = float(np.mean(np.array(preds) == np.array(truth)))
    tb = {}
    for lang in set(langs):
        idx = [i for i, l in enumerate(langs) if l == lang]
        if idx:
            tb[lang] = float(np.mean((np.array(preds)[idx]) == (np.array(truth)[idx])))
    conf_corr = float(np.mean([r["confidence"] for r in recs if ((r["pred_label"] == "AI_GENERATED") == (r["true_class"] == "ai"))]))
    conf_err = float(np.mean([r["confidence"] for r in recs if ((r["pred_label"] == "AI_GENERATED") != (r["true_class"] == "ai"))])) if any(((r["pred_label"] == "AI_GENERATED") != (r["true_class"] == "ai")) for r in recs) else 0.0
    lat = [r["latency_total_ms"] for r in recs]
    res = {"accuracy": acc, "per_language_accuracy": tb, "avg_confidence_correct": conf_corr, "avg_confidence_incorrect": conf_err, "avg_latency_ms": float(np.mean(lat)), "p95_latency_ms": float(np.percentile(lat, 95)), "p99_latency_ms": float(np.percentile(lat, 99)), "samples": recs, "total_time_ms": float((t1 - t0) * 1000.0)}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f)
    print("OK")


if __name__ == "__main__":
    main()
