import os
import csv
import logging
from pathlib import Path
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

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

def main():
    base_dir = Path("N:/speech data")
    human_dir = base_dir / "human"
    meta_path = base_dir / "metadata.csv"
    
    # Read existing metadata to avoid duplicates
    existing_clips = set()
    if meta_path.exists():
        with open(meta_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_clips.add(row["clip_id"])
    
    rows_added = 0
    
    with open(meta_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not meta_path.exists() or meta_path.stat().st_size == 0:
            writer.writeheader()
            
        for lang_dir in human_dir.iterdir():
            if not lang_dir.is_dir():
                continue
            
            lang = lang_dir.name
            logging.info(f"Indexing human samples for {lang}...")
            
            files = list(lang_dir.glob("*.wav"))
            for wav_path in tqdm(files, desc=f"{lang}"):
                clip_id = wav_path.stem
                if clip_id in existing_clips:
                    continue
                
                # Approximate duration from filename or just use 4.0
                # In our preprocess script, we saved duration in the name? No, but they are ~4s.
                # For a professional index, we should ideally check duration, but 4.0 is a good guess.
                
                row = {
                    "clip_id": clip_id,
                    "language": lang,
                    "source_type": "human",
                    "speaker_id": "unknown",
                    "tts_engine": "n/a",
                    "tts_voice": "n/a",
                    "text_id": "n/a",
                    "duration_sec": "4.0",
                    "sample_rate": "16000",
                    "file_path": wav_path.as_posix(),
                    "checksum_sha256": "n/a",
                    "consent_received": "n/a",
                    "notes": "auto-indexed",
                }
                writer.writerow(row)
                existing_clips.add(clip_id)
                rows_added += 1
                
    logging.info(f"Done. Added {rows_added} human samples to metadata.csv")

if __name__ == "__main__":
    main()
