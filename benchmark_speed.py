import os
import argparse
import json
import time
import numpy as np
from typing import Dict
from joblib import load
from app.services.classifier import LogisticClassifier
from app.services.detector import extract_features_pcm
from app.utils.audio import read_mp3_to_pcm_result
import psutil
import pathlib
ff = pathlib.Path("C:/ffmpeg/ffmpeg-master-latest-win64-gpl/bin")
if ff.exists():
    os.environ["PATH"] = os.environ.get("PATH", "") + ";" + str(ff)
    os.environ["FFMPEG_BINARY"] = str(ff / "ffmpeg.exe")
    os.environ["FFPROBE_BINARY"] = str(ff / "ffprobe.exe")


def load_weights() -> Dict:
    w = load("training_out/weights.pkl")
    return {"feature_names": w["feature_names"], "mu": np.array(w["mu"], dtype=np.float32), "sigma": np.array(w["sigma"], dtype=np.float32), "weights": np.array(w["weights"], dtype=np.float32), "bias": float(w["bias"]), "calib_a": float(w.get("calib_a", 1.0)), "calib_b": float(w.get("calib_b", 0.0))}


def discover_samples(base_dir: str, limit: int) -> list:
    items = []
    for cls in ["human", "ai"]:
        cdir = os.path.join(base_dir, cls)
        if not os.path.isdir(cdir):
            continue
        for lang in sorted(os.listdir(cdir)):
            ldir = os.path.join(cdir, lang)
            if not os.path.isdir(ldir):
                continue
            for fn in os.listdir(ldir):
                if fn.lower().endswith(".mp3"):
                    items.append(os.path.join(ldir, fn))
                    if len(items) >= limit:
                        return items
    return items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--samples", type=int, default=100)
    ap.add_argument("--base-dir", default="data")
    ap.add_argument("--output", default="results/benchmark_results.json")
    args = ap.parse_args()
    w = load_weights()
    clf = LogisticClassifier(w["feature_names"], w["mu"], w["sigma"], w["weights"], w["bias"], w["calib_a"], w["calib_b"])
    items = discover_samples(args.base_dir, args.samples)
    lat = []
    st_decode_b64 = []
    st_decode_pcm = []
    st_features = []
    st_classify = []
    rss = []
    for path in items:
        t0 = time.perf_counter()
        with open(path, "rb") as f:
            b64 = f.read()
        t1 = time.perf_counter()
        pcm = read_mp3_to_pcm_result(path)
        t2 = time.perf_counter()
        feats = extract_features_pcm(pcm)
        t3 = time.perf_counter()
        p = clf.predict_proba(feats)
        t4 = time.perf_counter()
        st_decode_b64.append((t1 - t0) * 1000.0)
        st_decode_pcm.append((t2 - t1) * 1000.0)
        st_features.append((t3 - t2) * 1000.0)
        st_classify.append((t4 - t3) * 1000.0)
        lat.append((t4 - t0) * 1000.0)
        rss.append(psutil.Process(os.getpid()).memory_info().rss / (1024.0 * 1024.0))
    res = {
        "mean_latency_ms": float(np.mean(lat)) if lat else 0.0,
        "median_latency_ms": float(np.median(lat)) if lat else 0.0,
        "p95_latency_ms": float(np.percentile(lat, 95)) if lat else 0.0,
        "p99_latency_ms": float(np.percentile(lat, 99)) if lat else 0.0,
        "mean_decode_b64_ms": float(np.mean(st_decode_b64)) if st_decode_b64 else 0.0,
        "mean_decode_pcm_ms": float(np.mean(st_decode_pcm)) if st_decode_pcm else 0.0,
        "mean_features_ms": float(np.mean(st_features)) if st_features else 0.0,
        "mean_classify_ms": float(np.mean(st_classify)) if st_classify else 0.0,
        "memory_rss_mb_mean": float(np.mean(rss)) if rss else 0.0,
        "count": len(items),
    }
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(res, f)
    print("OK")


if __name__ == "__main__":
    main()
