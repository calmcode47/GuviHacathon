import os
import csv
import argparse
import logging
from pathlib import Path
import shutil

LANGS = ["tamil", "english", "hindi", "malayalam", "telugu"]
META_FIELDS = [
    "clip_id",
    "language",
    "source_type",
    "speaker_id",
    "tts_engine",
    "tts_voice",
    "text_id",
    "duration_sec",
    "sample_rate",
    "file_path",
    "checksum_sha256",
    "consent_received",
    "notes",
]

def append_metadata(meta_csv: str, row: dict) -> None:
    exists = os.path.exists(meta_csv)
    with open(meta_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base-dir", default="data")
    p.add_argument("--speaker-id", default="proto")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = Path(args.base_dir)
    meta_csv = base / "metadata.csv"
    for lang in LANGS:
        ai_dir = base / "ai" / lang
        human_dir = base / "human" / lang
        human_dir.mkdir(parents=True, exist_ok=True)
        idx = 0
        for mp3 in sorted(ai_dir.glob("*.mp3")):
            clip_id = f"{lang}_{args.speaker_id}_{idx:03d}"
            dst = human_dir / f"{clip_id}.mp3"
            shutil.copy(mp3, dst)
            row = {
                "clip_id": clip_id,
                "language": lang,
                "source_type": "human",
                "speaker_id": args.speaker_id,
                "tts_engine": "",
                "tts_voice": "",
                "text_id": "",
                "duration_sec": "0.0",
                "sample_rate": "0",
                "file_path": dst.as_posix(),
                "checksum_sha256": "",
                "consent_received": "synthetic_prototype",
                "notes": "duplicated from AI for pipeline demo",
            }
            append_metadata(str(meta_csv), row)
            idx += 1
        logging.info("Duplicated %d files for %s into human/", idx, lang)

if __name__ == "__main__":
    main()
