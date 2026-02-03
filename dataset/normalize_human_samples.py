import os
import re
import csv
import argparse
import logging
import hashlib
import shutil
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
from mutagen.mp3 import MP3

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


def detect_language_from_path(path: str) -> str:
    parts = [p.lower() for p in re.split(r"[\\/]", path) if p]
    for lang in LANGS:
        if lang in parts:
            return lang
    return ""


def scan_mp3s(path: str) -> List[str]:
    files = []
    for root, _, fns in os.walk(path):
        for fn in fns:
            if fn.lower().endswith(".mp3"):
                files.append(os.path.join(root, fn))
    return files


def validate_mp3(path: str) -> Tuple[bool, float, int, int]:
    try:
        audio = MP3(path)
        duration = float(audio.info.length or 0.0)
        sr = int(getattr(audio.info, "sample_rate", 0))
        ch = int(getattr(audio.info, "channels", 0))
        valid = duration >= 1.0 and sr >= 16000 and sr <= 48000 and ch in (1, 2)
        return valid, duration, sr, ch
    except Exception:
        return False, 0.0, 0, 0


def checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def load_existing_checksums(meta_csv: str) -> Dict[str, Dict[str, str]]:
    checks = {}
    if os.path.exists(meta_csv):
        with open(meta_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                cs = row.get("checksum_sha256", "")
                if cs:
                    checks[cs] = row
    return checks


def next_index(meta_csv: str, language: str, speaker_id: str) -> int:
    idx = 1
    if os.path.exists(meta_csv):
        with open(meta_csv, "r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                if row.get("source_type") == "human" and row.get("language") == language and row.get("speaker_id") == speaker_id:
                    m = re.search(rf"{language}_{speaker_id}_(\d+)", row.get("clip_id", ""))
                    if m:
                        idx = max(idx, int(m.group(1)) + 1)
    return idx


def append_metadata(meta_csv: str, row: Dict[str, str]) -> None:
    exists = os.path.exists(meta_csv)
    with open(meta_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", required=True)
    parser.add_argument("--language", default="")
    parser.add_argument("--speaker-id", required=True)
    parser.add_argument("--base-dir", default="data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    lang = args.language.strip().lower()
    if not lang:
        lang = detect_language_from_path(args.input_dir)
    if not lang:
        try:
            lang = input(f"Enter language ({', '.join(LANGS)}): ").strip().lower()
        except Exception:
            lang = ""
    if lang not in LANGS:
        logging.error("Language not detected or invalid")
        return
    target_dir = os.path.join(args.base_dir, "human", lang)
    os.makedirs(target_dir, exist_ok=True)
    meta_csv = os.path.join(args.base_dir, "metadata.csv")
    existing = load_existing_checksums(meta_csv)
    files = scan_mp3s(args.input_dir)
    idx = next_index(meta_csv, lang, args.speaker_id)
    pbar = tqdm(files, desc="Normalizing human samples")
    for src in pbar:
        ok, dur, sr, ch = validate_mp3(src)
        if not ok:
            logging.warning("Invalid MP3 skipped: %s", src)
            continue
        cs = checksum(src)
        if cs in existing:
            logging.info("Duplicate skipped: %s", src)
            continue
        clip_id = f"{lang}_{args.speaker_id}_{idx:03d}"
        dst = os.path.join(target_dir, f"{clip_id}.mp3")
        while os.path.exists(dst):
            idx += 1
            clip_id = f"{lang}_{args.speaker_id}_{idx:03d}"
            dst = os.path.join(target_dir, f"{clip_id}.mp3")
        shutil.move(src, dst)
        row = {
            "clip_id": clip_id,
            "language": lang,
            "source_type": "human",
            "speaker_id": args.speaker_id,
            "tts_engine": "",
            "tts_voice": "",
            "text_id": "",
            "duration_sec": f"{dur:.3f}",
            "sample_rate": str(sr),
            "file_path": Path(dst).as_posix(),
            "checksum_sha256": cs,
            "consent_received": "unknown",
            "notes": "",
        }
        append_metadata(meta_csv, row)
        existing[cs] = row
        idx += 1
    logging.info("Normalization complete: %s", target_dir)


if __name__ == "__main__":
    main()
