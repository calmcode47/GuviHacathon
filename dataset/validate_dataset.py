import os
import argparse
import logging
import csv
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm
from mutagen.mp3 import MP3

LANGS = ["tamil", "english", "hindi", "malayalam", "telugu"]


def scan_files(base_dir: str) -> List[Dict[str, str]]:
    rows = []
    for source in ["human", "ai"]:
        for lang in LANGS:
            d = os.path.join(base_dir, source, lang)
            if not os.path.isdir(d):
                continue
            for root, _, files in os.walk(d):
                for fn in files:
                    if fn.lower().endswith(".mp3"):
                        rows.append({
                            "source": source,
                            "language": lang,
                            "path": os.path.join(root, fn),
                        })
    return rows


def validate_row(path: str) -> Dict[str, str]:
    issues = []
    try:
        audio = MP3(path)
        duration = float(audio.info.length or 0.0)
        sr = int(getattr(audio.info, "sample_rate", 0))
        ch = int(getattr(audio.info, "channels", 0))
        if duration < 15.0 or duration > 60.0:
            issues.append("duration_out_of_range")
        if sr < 16000 or sr > 48000:
            issues.append("sample_rate_out_of_range")
        if ch not in (1, 2):
            issues.append("channels_invalid")
        valid = "yes" if len(issues) == 0 else "no"
        return {
            "duration_sec": f"{duration:.3f}",
            "sample_rate": str(sr),
            "channels": str(ch),
            "valid": valid,
            "issues": ";".join(issues),
        }
    except Exception as e:
        return {
            "duration_sec": "0.0",
            "sample_rate": "0",
            "channels": "0",
            "valid": "no",
            "issues": f"corrupt:{str(e)}",
        }


def write_report(rows: List[Dict[str, str]], out_csv: str) -> None:
    fields = ["source", "language", "path", "duration_sec", "sample_rate", "channels", "valid", "issues"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def split_recommendations(rows: List[Dict[str, str]], out_csv: str) -> None:
    counts = {}
    for r in rows:
        if r["valid"] != "yes":
            continue
        key = (r["source"], r["language"])
        counts[key] = counts.get(key, 0) + 1
    fields = ["source", "language", "total", "train", "val", "test"]
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for (source, language), total in counts.items():
            train = int(round(total * 0.70))
            val = int(round(total * 0.15))
            test = max(0, total - train - val)
            w.writerow({
                "source": source,
                "language": language,
                "total": total,
                "train": train,
                "val": val,
                "test": test,
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    root = Path(__file__).resolve().parents[1]
    parser.add_argument("--base-dir", default=str(root / "data"))
    parser.add_argument("--report-csv", default=str(root / "dataset" / "validation_report.csv"))
    parser.add_argument("--splits-csv", default=str(root / "dataset" / "split_recommendations.csv"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    files = scan_files(args.base_dir)
    results = []
    for r in tqdm(files, desc="Validating MP3s"):
        v = validate_row(r["path"])
        out = {**r, **v}
        results.append(out)
    write_report(results, args.report_csv)
    split_recommendations(results, args.splits_csv)
    logging.info("Report: %s", args.report_csv)
    logging.info("Splits: %s", args.splits_csv)


if __name__ == "__main__":
    main()
