import os
import argparse
import json
import numpy as np
from joblib import load


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--weights", default="training_out/weights.pkl")
    ap.add_argument("--output", default="app/model/model.json")
    args = ap.parse_args()
    w = load(args.weights)
    names = w.get("feature_names", [])
    mu = np.array(w["mu"], dtype=np.float32).tolist()
    sigma = np.array(w["sigma"], dtype=np.float32).tolist()
    weights = np.array(w["weights"], dtype=np.float32).tolist()
    bias = float(w["bias"])
    a = float(w.get("calib_a", 8.0))
    c = float(w.get("calib_b", 0.0))
    obj = {
        "feature_names": names,
        "mean": mu,
        "std": sigma,
        "mu": mu,
        "sigma": sigma,
        "weights": weights,
        "bias": bias,
        "calib_a": 8.0,
        "calib_c": c,
    }
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(obj, f)
    with open(args.output, "r", encoding="utf-8") as f:
        _ = json.load(f)
    print("OK")


if __name__ == "__main__":
    main()
