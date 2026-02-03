import os
import argparse
import logging
import hashlib
from typing import Dict
import numpy as np
import soundfile as sf
from tqdm import tqdm
from datasets import load_dataset
from mutagen.mp3 import MP3
from pydub import AudioSegment

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


def append_metadata(meta_path: str, row: Dict[str, str]) -> None:
    exists = os.path.exists(meta_path)
    with open(meta_path, "a", newline="", encoding="utf-8") as f:
        import csv
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def ffmpeg_available() -> bool:
    from pydub.utils import which
    if os.getenv("FFMPEG_BINARY"):
        return True
    return which("ffmpeg") is not None


def save_array_to_mp3(arr: np.ndarray, sr: int, out_path: str) -> Dict[str, float]:
    tmp_wav = out_path.replace(".mp3", ".wav")
    sf.write(tmp_wav, arr.astype(np.float32), sr)
    seg = AudioSegment.from_wav(tmp_wav)
    seg = seg.set_frame_rate(sr)
    seg.export(out_path, format="mp3")
    try:
        os.remove(tmp_wav)
    except Exception:
        pass
    try:
        info = MP3(out_path)
        dur = float(info.info.length or 0.0)
        sr2 = int(getattr(info.info, "sample_rate", sr))
        return {"duration_sec": dur, "sample_rate": sr2}
    except Exception:
        return {"duration_sec": float(seg.duration_seconds), "sample_rate": sr}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data")
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--split", default="train")
    parser.add_argument("--config", default="clean")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not ffmpeg_available():
        logging.error("FFmpeg not available; cannot export MP3")
        return
    out_dir = os.path.join(args.base_dir, "human", "english")
    ensure_dir(out_dir)
    meta_csv = os.path.join(args.base_dir, "metadata.csv")
    try:
        ds = load_dataset("MLCommons/peoples_speech", args.config, split=args.split, streaming=True)
    except Exception as e:
        logging.error("Failed to load People’s Speech: %s", str(e))
        return
    count = 0
    pbar = tqdm(total=args.max, desc="Downloading People’s Speech (english)")
    for ex in ds:
        if count >= args.max:
            break
        audio = ex.get("audio", {})
        sr = int(audio.get("sampling_rate", 0))
        arr = np.array(audio.get("array", []), dtype=np.float32)
        if arr.size == 0 or sr <= 0:
            continue
        clip_id = f"english_ps_{count:05d}"
        out_path = os.path.join(out_dir, f"{clip_id}.mp3")
        try:
            info = save_array_to_mp3(arr, sr, out_path)
            sha = checksum(out_path)
            row = {
                "clip_id": clip_id,
                "language": "english",
                "source_type": "human",
                "speaker_id": "peoples_speech",
                "tts_engine": "",
                "tts_voice": "",
                "text_id": str(ex.get("id", i)),
                "duration_sec": f"{info.get('duration_sec', 0.0):.3f}",
                "sample_rate": str(info.get("sample_rate", sr)),
                "file_path": out_path.replace("\\", "/"),
                "checksum_sha256": sha,
                "consent_received": "open_dataset",
                "notes": f"MLCommons/peoples_speech:{args.config}/{args.split}",
            }
            append_metadata(meta_csv, row)
            count += 1
            pbar.update(1)
        except Exception as e:
            logging.warning("Failed to save sample #%d: %s", i, str(e))
    logging.info("Completed People’s Speech import")


if __name__ == "__main__":
    main()
