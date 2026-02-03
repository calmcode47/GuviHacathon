import os
import argparse
import logging
import hashlib
from typing import Dict
import numpy as np
import soundfile as sf
from tqdm import tqdm
from datasets import load_dataset, Audio
from mutagen.mp3 import MP3
from pydub import AudioSegment
import subprocess

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
    ff = os.getenv("FFMPEG_BINARY") or "ffmpeg"
    try:
        subprocess.run([ff, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except Exception:
        return False


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

def convert_to_mp3_ffmpeg(in_path: str, sr: int, out_path: str) -> Dict[str, float]:
    ff = os.getenv("FFMPEG_BINARY") or "ffmpeg"
    cmd = [ff, "-y", "-i", in_path, "-ar", str(sr), "-vn", "-ac", "1", "-b:a", "192k", out_path]
    subprocess.run(cmd, check=True)
    try:
        info = MP3(out_path)
        dur = float(info.info.length or 0.0)
        sr2 = int(getattr(info.info, "sample_rate", sr))
    except Exception:
        dur = 0.0
        sr2 = sr
    return {"duration_sec": dur, "sample_rate": sr2}

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data")
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--split", default="train")
    parser.add_argument("--config", default="clean")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    # Proceed even if pre-check fails; conversion will raise per-file if unavailable
    out_dir = os.path.join(args.base_dir, "human", "english")
    ensure_dir(out_dir)
    meta_csv = os.path.join(args.base_dir, "metadata.csv")
    try:
        ds = load_dataset("MLCommons/peoples_speech", args.config, split=f"{args.split}[:{args.max}]")
        ds = ds.cast_column("audio", Audio(decode=False))
    except Exception as e:
        logging.error("Failed to load People’s Speech: %s", str(e))
        return
    pbar = tqdm(range(len(ds)), desc="Downloading People’s Speech (english) - path mode")
    for i in pbar:
        ex = ds[i]
        audio = ex.get("audio", {})
        sr = int(audio.get("sampling_rate", 16000))
        in_path = audio.get("path", "")
        bdata = audio.get("bytes", None)
        if sr <= 0:
            continue
        clip_id = f"english_ps_{i+1:05d}"
        out_path = os.path.join(out_dir, f"{clip_id}.mp3")
        try:
            if bdata:
                tmp_flac = os.path.join(out_dir, f"tmp_{clip_id}.flac")
                with open(tmp_flac, "wb") as wf:
                    wf.write(bdata)
                info = convert_to_mp3_ffmpeg(tmp_flac, sr, out_path)
                try:
                    os.remove(tmp_flac)
                except Exception:
                    pass
            elif in_path:
                info = convert_to_mp3_ffmpeg(in_path, sr, out_path)
            else:
                continue
            dur = info.get("duration_sec", 0.0)
            sr2 = int(info.get("sample_rate", sr))
            sha = checksum(out_path)
            row = {
                "clip_id": clip_id,
                "language": "english",
                "source_type": "human",
                "speaker_id": "peoples_speech",
                "tts_engine": "",
                "tts_voice": "",
                "text_id": str(ex.get("id", i)),
                "duration_sec": f"{dur:.3f}",
                "sample_rate": str(sr2),
                "file_path": out_path.replace("\\", "/"),
                "checksum_sha256": sha,
                "consent_received": "open_dataset",
                "notes": f"MLCommons/peoples_speech:{args.config}/{args.split}",
            }
            append_metadata(meta_csv, row)
        except Exception as e:
            logging.warning("Failed to save sample #%d: %s", i, str(e))
    logging.info("Completed People’s Speech import")


if __name__ == "__main__":
    main()
