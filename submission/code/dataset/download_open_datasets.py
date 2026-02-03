import os
import csv
import argparse
import logging
from pathlib import Path
import hashlib
import shutil
import numpy as np
import soundfile as sf
from tqdm import tqdm
from datasets import load_dataset
from mutagen.mp3 import MP3
from pydub import AudioSegment

LANGS = ["tamil", "english", "hindi", "malayalam", "telugu"]
LANG_CODES = {"tamil": "ta", "english": "en", "hindi": "hi", "malayalam": "ml", "telugu": "te"}
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


def ensure_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def append_metadata(meta_path: str, row: dict) -> None:
    exists = os.path.exists(meta_path)
    with open(meta_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def try_load_common_voice(lang_code: str, versions: list, limit: int):
    for v in versions:
        name = f"mozilla-foundation/common_voice_{v}"
        try:
            split = f"train[:{limit}]"
            ds = load_dataset(name, lang_code, split=split)
            return ds, v
        except Exception:
            continue
    raise RuntimeError("Failed to load Common Voice for language code")


def save_example_to_mp3(example: dict, out_path: str) -> tuple:
    audio = example.get("audio", {})
    sr = int(audio.get("sampling_rate", 0))
    path = example.get("path") or audio.get("path")
    if path and path.lower().endswith(".mp3"):
        shutil.copy(path, out_path)
        try:
            info = MP3(out_path)
            dur = float(info.info.length or 0.0)
            sr2 = int(getattr(info.info, "sample_rate", sr))
            return dur, sr2
        except Exception:
            return 0.0, sr
    arr = np.array(audio.get("array", []), dtype=np.float32)
    tmp_wav = out_path.replace(".mp3", ".wav")
    sf.write(tmp_wav, arr, sr if sr > 0 else 22050)
    seg = AudioSegment.from_wav(tmp_wav)
    seg = seg.set_frame_rate(sr if sr > 0 else 22050)
    seg.export(out_path, format="mp3")
    try:
        os.remove(tmp_wav)
    except Exception:
        pass
    return float(seg.duration_seconds), int(sr if sr > 0 else 22050)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data")
    parser.add_argument("--languages", nargs="*", default=LANGS)
    parser.add_argument("--max-per-language", type=int, default=100)
    parser.add_argument("--versions", nargs="*", default=["17_0", "16_0", "13_0"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ensure_dir(args.base_dir)
    meta_csv = os.path.join(args.base_dir, "metadata.csv")
    for lang in args.languages:
        code = LANG_CODES.get(lang, "")
        if not code:
            logging.warning("Skipping unknown language: %s", lang)
            continue
        out_dir = os.path.join(args.base_dir, "human", lang)
        ensure_dir(out_dir)
        try:
            ds, ver = try_load_common_voice(code, args.versions, args.max_per_language)
        except Exception as e:
            logging.error("Failed to load dataset for %s: %s", lang, str(e))
            continue
        pbar = tqdm(range(len(ds)), desc=f"Downloading {lang}")
        for i in pbar:
            ex = ds[i]
            clip_id = f"{lang}_cv_{i:03d}"
            out_path = os.path.join(out_dir, f"{clip_id}.mp3")
            try:
                dur, sr = save_example_to_mp3(ex, out_path)
                sha = checksum(out_path)
                row = {
                    "clip_id": clip_id,
                    "language": lang,
                    "source_type": "human",
                    "speaker_id": f"cv-{ver}",
                    "tts_engine": "",
                    "tts_voice": "",
                    "text_id": f"{lang}_{i:03d}",
                    "duration_sec": f"{dur:.3f}",
                    "sample_rate": str(sr),
                    "file_path": Path(out_path).as_posix(),
                    "checksum_sha256": sha,
                    "consent_received": "open_dataset",
                    "notes": f"common_voice_{ver}:{code}",
                }
                append_metadata(meta_csv, row)
            except Exception as e:
                logging.warning("Failed example %s #%d: %s", lang, i, str(e))
        logging.info("Completed %s", lang)


if __name__ == "__main__":
    main()
