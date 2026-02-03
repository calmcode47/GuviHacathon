import os
import argparse
import json
from typing import Dict
import numpy as np
from app.services.classifier import LogisticClassifier, get_default_classifier
from app.services.detector import extract_features_pcm
from app.utils.audio import read_mp3_to_pcm_result
import pathlib
ff = pathlib.Path("C:/ffmpeg/ffmpeg-master-latest-win64-gpl/bin")
if ff.exists():
    os.environ["PATH"] = os.environ.get("PATH", "") + ";" + str(ff)
    os.environ["FFMPEG_BINARY"] = str(ff / "ffmpeg.exe")
    os.environ["FFPROBE_BINARY"] = str(ff / "ffprobe.exe")


def load_json_model(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    return obj


def validate_structure(obj: Dict) -> Dict[str, str]:
    issues = {}
    for k in ["mu", "std", "weights", "bias"]:
        if k not in obj and (k == "std" and "sigma" in obj):
            continue
        if k not in obj:
            issues[k] = "missing"
    if "calib_a" not in obj and "calib_c" not in obj:
        issues["calib_a/c"] = "missing"
    names = obj.get("feature_names", [])
    if len(names) != 10:
        issues["feature_names"] = "expected 10 features"
    return issues


def build_classifier(obj: Dict) -> LogisticClassifier:
    names = obj.get("feature_names", [])
    mu = np.array(obj["mu"], dtype=np.float32)
    sigma = np.array(obj["std"] if "std" in obj else obj["sigma"], dtype=np.float32)
    weights = np.array(obj["weights"], dtype=np.float32)
    bias = float(obj["bias"])
    a = float(obj.get("calib_a", obj.get("calib_c", 1.0)))
    b = float(obj.get("calib_b", 0.0))
    return LogisticClassifier(names, mu, sigma, weights, bias, a, b)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="app/model/model.json")
    ap.add_argument("--sample", default="")
    args = ap.parse_args()
    result = {"status": "ok", "issues": {}}
    clf = None
    if os.path.isfile(args.model):
        obj = load_json_model(args.model)
        issues = validate_structure(obj)
        result["issues"] = issues
        clf = build_classifier(obj)
    else:
        clf = get_default_classifier()
    path = args.sample
    if not path:
        base = "data/human/english"
        for root, _, files in os.walk(base):
            for fn in files:
                if fn.lower().endswith(".mp3"):
                    path = os.path.join(root, fn)
                    break
            if path:
                break
    pcm = read_mp3_to_pcm_result(path)
    feats = extract_features_pcm(pcm)
    p = clf.predict_proba(feats)
    label = "AI_GENERATED" if p >= 0.5 else "HUMAN"
    conf = p if label == "AI_GENERATED" else (1.0 - p)
    ok = 0.0 <= conf <= 1.0
    result["prediction"] = {"label": label, "confidence": float(conf), "p_ai": float(p), "ok_confidence_range": bool(ok)}
    out = "results"
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "verify_api.json"), "w", encoding="utf-8") as f:
        json.dump(result, f)
    print("OK")


if __name__ == "__main__":
    main()
