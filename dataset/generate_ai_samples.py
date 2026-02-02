import os
import csv
import asyncio
import hashlib
import argparse
import logging
from typing import List, Dict
from tqdm import tqdm
from pydub import AudioSegment
from gtts import gTTS
import edge_tts
import pyttsx3
import shutil

LANG_CODES = {
    "english": "en",
    "tamil": "ta",
    "hindi": "hi",
    "malayalam": "ml",
    "telugu": "te",
}

EDGE_VOICES = {
    "english": "en-US-AriaNeural",
    "tamil": "ta-IN-PallaviNeural",
    "hindi": "hi-IN-SwaraNeural",
    "malayalam": "ml-IN-MidhunNeural",
    "telugu": "te-IN-ShrutiNeural",
}

ENGINES = ["gtts", "edge", "pyttsx3"]
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

def ffmpeg_available() -> bool:
    from pydub.utils import which
    if os.getenv("FFMPEG_BINARY"):
        return True
    return which("ffmpeg") is not None

def read_corpus(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f.readlines()]
    words_ok = [ln for ln in lines if 5 <= len(ln.split()) <= 50]
    return words_ok if len(words_ok) >= 1 else lines


def checksum(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def export_with_sr(mp3_path: str, target_sr: int) -> Dict[str, float]:
    if ffmpeg_available():
        seg = AudioSegment.from_file(mp3_path, format="mp3")
        seg = seg.set_frame_rate(target_sr)
        seg.export(mp3_path, format="mp3")
        return {"duration_sec": seg.duration_seconds, "sample_rate": target_sr}
    else:
        try:
            from mutagen.mp3 import MP3
            info = MP3(mp3_path)
            dur = float(info.info.length or 0.0)
            sr = int(getattr(info.info, "sample_rate", target_sr))
            return {"duration_sec": dur, "sample_rate": sr}
        except Exception:
            return {"duration_sec": 0.0, "sample_rate": target_sr}


def synth_gtts(text: str, lang: str, out_path: str, target_sr: int) -> Dict[str, float]:
    tts = gTTS(text=text, lang=lang)
    tts.save(out_path)
    return export_with_sr(out_path, target_sr)


async def synth_edge_async(text: str, voice: str, out_path: str, target_sr: int) -> Dict[str, float]:
    comm = edge_tts.Communicate(text=text, voice=voice)
    await comm.save(out_path)
    return export_with_sr(out_path, target_sr)


def synth_pyttsx3(text: str, out_path: str, target_sr: int) -> Dict[str, float]:
    if not ffmpeg_available():
        raise RuntimeError("ffmpeg not available for pyttsx3 conversion")
    tmp_wav = out_path.replace(".mp3", ".wav")
    engine = pyttsx3.init()
    engine.save_to_file(text, tmp_wav)
    engine.runAndWait()
    seg = AudioSegment.from_wav(tmp_wav)
    seg = seg.set_frame_rate(target_sr)
    seg.export(out_path, format="mp3")
    try:
        os.remove(tmp_wav)
    except Exception:
        pass
    return {"duration_sec": seg.duration_seconds, "sample_rate": target_sr}


def append_metadata(meta_path: str, row: Dict[str, str]) -> None:
    exists = os.path.exists(meta_path)
    with open(meta_path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=META_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-dir", default="data")
    parser.add_argument("--corpus-dir", default="dataset/corpus")
    parser.add_argument("--samples-per-language", type=int, default=50)
    parser.add_argument("--target-sample-rate", type=int, default=22050)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    base = args.base_dir
    meta_path = os.path.join(base, "metadata.csv")
    langs = ["tamil", "english", "hindi", "malayalam", "telugu"]
    for lang in langs:
        out_dir = os.path.join(base, "ai", lang)
        os.makedirs(out_dir, exist_ok=True)
        corpus_file = os.path.join(args.corpus_dir, f"{lang}.txt")
        sentences = read_corpus(corpus_file)
        if len(sentences) < args.samples_per_language:
            logging.warning("Corpus too small for %s: %d", lang, len(sentences))
        count = 0
        pbar = tqdm(total=args.samples_per_language, desc=f"{lang} AI samples")
        for i in range(args.samples_per_language):
            if i >= len(sentences):
                break
            text = sentences[i]
            clip_id = f"{lang}_ai_{i:03d}"
            out_path = os.path.join(out_dir, f"{clip_id}.mp3")
            engine_name = ENGINES[i % len(ENGINES)]
            ok = False
            info = {}
            try:
                if engine_name == "gtts":
                    info = synth_gtts(text, LANG_CODES[lang], out_path, args.target_sample_rate)
                    ok = True
                    voice = ""
                elif engine_name == "edge":
                    voice = EDGE_VOICES.get(lang, "")
                    info = asyncio.run(synth_edge_async(text, voice, out_path, args.target_sample_rate))
                    ok = True
                else:
                    info = synth_pyttsx3(text, out_path, args.target_sample_rate)
                    ok = True
                    voice = ""
            except Exception as e:
                logging.warning("Engine %s failed for %s #%d: %s", engine_name, lang, i, str(e))
            if not ok:
                try:
                    info = synth_gtts(text, LANG_CODES[lang], out_path, args.target_sample_rate)
                    ok = True
                    voice = ""
                except Exception as e2:
                    logging.error("Fallback gTTS failed for %s #%d: %s", lang, i, str(e2))
            if ok:
                sha = checksum(out_path)
                row = {
                    "clip_id": clip_id,
                    "language": lang,
                    "source_type": "ai",
                    "speaker_id": "",
                    "tts_engine": engine_name if engine_name != "edge" else "edge-tts",
                    "tts_voice": voice if engine_name == "edge" else "",
                    "text_id": f"{lang}_{i:03d}",
                    "duration_sec": f"{info.get('duration_sec', 0.0):.3f}",
                    "sample_rate": str(info.get("sample_rate", args.target_sample_rate)),
                    "file_path": out_path.replace("\\", "/"),
                    "checksum_sha256": sha,
                    "consent_received": "n/a",
                    "notes": "",
                }
                append_metadata(meta_path, row)
                count += 1
                pbar.update(1)
        pbar.close()
        logging.info("Generated %d/%d for %s", count, args.samples_per_language, lang)


if __name__ == "__main__":
    main()
