import argparse
import json
from pathlib import Path
from joblib import load

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--weights", default="training_out/weights.pkl")
    p.add_argument("--output", default="app/model/model.json")
    args = p.parse_args()
    w = load(args.weights)
    obj = {
        "feature_names": [str(x) for x in w["feature_names"]],
        "mu": [float(x) for x in w["mu"]],
        "sigma": [float(x) for x in w["sigma"]],
        "weights": [float(x) for x in w["weights"]],
        "bias": float(w["bias"]),
        "calib_a": float(w.get("calib_a", 1.0)),
        "calib_b": float(w.get("calib_b", 0.0)),
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(obj), encoding="utf-8")

if __name__ == "__main__":
    main()
