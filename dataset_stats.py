import os
import argparse
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mutagen.mp3 import MP3


def scan_dir(base_dir: str):
    stats = {}
    total_sec = 0.0
    for cls in ["human", "ai"]:
        cdir = os.path.join(base_dir, cls)
        if not os.path.isdir(cdir):
            continue
        for lang in sorted(os.listdir(cdir)):
            ldir = os.path.join(cdir, lang)
            if not os.path.isdir(ldir):
                continue
            files = [os.path.join(ldir, f) for f in os.listdir(ldir) if f.lower().endswith(".mp3")]
            durs = []
            srs = []
            for p in files:
                try:
                    info = MP3(p)
                    durs.append(float(info.info.length or 0.0))
                    srs.append(int(getattr(info.info, "sample_rate", 0)))
                except Exception:
                    pass
            total_sec += float(np.sum(durs))
            stats.setdefault(lang, {"human": 0, "ai": 0, "durations": [], "sample_rates": []})
            stats[lang][cls] += len(files)
            stats[lang]["durations"].extend(durs)
            stats[lang]["sample_rates"].extend(srs)
    return stats, total_sec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-dir", default="data")
    ap.add_argument("--output", default="results/dataset_report.json")
    args = ap.parse_args()
    stats, total_sec = scan_dir(args.base_dir)
    report = {"per_language": {}, "total_hours": float(total_sec / 3600.0)}
    for lang, d in stats.items():
        hr = float(np.sum(d["durations"]) / 3600.0)
        sr_dist = {}
        for sr in d["sample_rates"]:
            if sr <= 0:
                continue
            sr_dist[str(sr)] = sr_dist.get(str(sr), 0) + 1
        report["per_language"][lang] = {"human_samples": int(d["human"]), "ai_samples": int(d["ai"]), "avg_duration_sec": float(np.mean(d["durations"])) if d["durations"] else 0.0, "sample_rate_distribution": sr_dist, "hours": hr}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f)
    langs = list(report["per_language"].keys())
    human = [report["per_language"][l]["human_samples"] for l in langs]
    ai = [report["per_language"][l]["ai_samples"] for l in langs]
    plt.figure(figsize=(8, 5))
    x = np.arange(len(langs))
    plt.bar(x - 0.2, human, width=0.4, label="human")
    plt.bar(x + 0.2, ai, width=0.4, label="ai")
    plt.xticks(x, langs, rotation=45, ha="right")
    plt.legend()
    plt.title("Class Balance per Language")
    out_dir = os.path.dirname(args.output) or "."
    plt.tight_layout()
    plt.savefig(os.path.join(out_dir, "dataset_balance.png"))
    print("OK")


if __name__ == "__main__":
    main()
