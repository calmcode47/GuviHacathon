import os
import argparse
from typing import Any, Dict
import json
import re
import numpy as np
from joblib import load


def to_array_str(arr: np.ndarray) -> str:
    vals = ", ".join([str(float(x)) for x in arr.tolist()])
    return f"np.array([{vals}], dtype=np.float32)"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", default="training_out/weights.pkl")
    parser.add_argument("--classifier-path", default="app/services/classifier.py")
    args = parser.parse_args()
    w = load(args.weights)
    with open(args.classifier_path, "r", encoding="utf-8") as f:
        src = f.read()
    bak = args.classifier_path + ".bak"
    with open(bak, "w", encoding="utf-8") as f:
        f.write(src)
    names = w["feature_names"]
    mu = np.array(w["mu"], dtype=np.float32)
    sigma = np.array(w["sigma"], dtype=np.float32)
    weights = np.array(w["weights"], dtype=np.float32)
    bias = float(w["bias"])
    calib_a = float(w.get("calib_a", 1.0))
    calib_b = float(w.get("calib_b", 0.0))
    pattern = r"(names\s*=\s*\[[\s\S]*?]\s*[\r\n]+)\s*mu\s*=\s*np\.array\([\s\S]*?\)[\s\S]*?sigma\s*=\s*np\.array\([\s\S]*?\)[\s\S]*?weights\s*=\s*np\.array\([\s\S]*?\)[\s\S]*?bias\s*=\s*[\s\S]*?calib_a\s*=\s*[\s\S]*?calib_b\s*=\s*[\s\S]*?return LogisticClassifier"
    if "return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)" not in src:
        print("Unexpected classifier signature")
        return
    block = []
    block.append("    names = [\n")
    for n in names:
        block.append(f"        \"{n}\",\n")
    block.append("    ]\n")
    block.append(f"    mu = {to_array_str(mu)}\n")
    block.append(f"    sigma = {to_array_str(sigma)}\n")
    block.append(f"    weights = {to_array_str(weights)}\n")
    block.append(f"    bias = {bias}\n")
    block.append(f"    calib_a = {calib_a}\n")
    block.append(f"    calib_b = {calib_b}\n")
    block.append("    return LogisticClassifier(names, mu, sigma, weights, bias, calib_a, calib_b)\n")
    new_src = re.sub(r"names\s*=\s*\[[\s\S]*?return LogisticClassifier\(names, mu, sigma, weights, bias, calib_a, calib_b\)", "".join(block), src)
    with open(args.classifier_path, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("Updated classifier with trained weights")


if __name__ == "__main__":
    main()
