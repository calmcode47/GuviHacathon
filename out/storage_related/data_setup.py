import os
import csv
import argparse
import logging
from tqdm import tqdm

LANGUAGES = ["tamil", "english", "hindi", "malayalam", "telugu"]
CATEGORIES = ["human", "ai"]
METADATA_FIELDS = [
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


def write_gitkeep(path: str) -> None:
    p = os.path.join(path, ".gitkeep")
    if not os.path.exists(p):
        with open(p, "w", encoding="utf-8") as f:
            f.write("")


def write_metadata_template(base_dir: str) -> None:
    mpath = os.path.join(base_dir, "metadata.csv")
    if not os.path.exists(mpath):
        with open(mpath, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=METADATA_FIELDS)
            w.writeheader()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = args.base_dir
    ensure_dir(base)
    tasks = []
    for cat in CATEGORIES:
        for lang in LANGUAGES:
            tasks.append(os.path.join(base, cat, lang))
    for d in tqdm(tasks, desc="Creating directories"):
        ensure_dir(d)
        write_gitkeep(d)
    write_metadata_template(base)
    ok = all(os.path.isdir(os.path.join(base, c, l)) for c in CATEGORIES for l in LANGUAGES)
    logging.info("Structure OK: %s", "yes" if ok else "no")
    logging.info("Metadata template: %s", os.path.join(base, "metadata.csv"))


if __name__ == "__main__":
    main()
