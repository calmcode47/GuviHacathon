import os
import argparse
import logging
import librosa
import soundfile as sf
import numpy as np
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

CHUNK_DURATION = 4.0  # seconds
TARGET_SR = 16000     # 16 kHz

def process_file(input_path: Path, output_dir: Path, language: str):
    """
    Loads an audio file, converts to mono 16kHz, segments into 4s chunks.
    Saves chunks to output_dir/human/language/.
    """
    try:
        # librosa.load automatically converts to mono and resamples if sr is provided
        y, sr = librosa.load(input_path, sr=TARGET_SR, mono=True)
    except Exception as e:
        logging.error(f"Failed to load {input_path}: {e}")
        return

    # Remove extreme silence (optional but recommended for voice data)
    y, _ = librosa.effects.trim(y, top_db=30)
    
    total_duration = len(y) / sr
    if total_duration < 2.0:
        logging.warning(f"Skipping {input_path}, too short ({total_duration:.2f}s)")
        return
        
    chunk_samples = int(CHUNK_DURATION * sr)
    base_name = input_path.stem.replace(" ", "_")
    
    out_lang_dir = output_dir / "human" / language.lower()
    out_lang_dir.mkdir(parents=True, exist_ok=True)
    
    num_chunks = int(np.ceil(len(y) / chunk_samples))
    
    for i in range(num_chunks):
        start_sample = i * chunk_samples
        end_sample = min((i + 1) * chunk_samples, len(y))
        
        chunk = y[start_sample:end_sample]
        chunk_dur = len(chunk) / sr
        
        # Only keep chunks longer than 2.5 seconds
        if chunk_dur < 2.5:
            continue
            
        out_name = f"{language.lower()}_human_{base_name}_{i:03d}.wav"
        out_path = out_lang_dir / out_name
        
        sf.write(str(out_path), chunk, sr)
        logging.info(f"Saved {out_path} ({chunk_dur:.2f}s)")

def main():
    parser = argparse.ArgumentParser(description="Preprocess Real Human Voice Recordings")
    parser.add_argument("--input-dir", required=True, help="Directory containing raw human voices (organized by language or loosely)")
    parser.add_argument("--output-dir", default="data", help="Base output directory (will write to output-dir/human/<lang>)")
    parser.add_argument("--language", default=None, help="Language if input-dir contains only one language")
    
    args = parser.parse_args()
    
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)
    
    valid_langs = ["tamil", "telugu", "telgu", "malayalam", "hindi", "english"]
    
    if not in_dir.exists():
        logging.error(f"Input directory does not exist: {in_dir}")
        return
        
    for root, _, files in os.walk(in_dir):
        root_path = Path(root)
        for f in files:
            if f.lower().endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
                # Try to infer language from directory name if not provided
                lang = args.language
                if not lang:
                    for l in valid_langs:
                        if l in str(root_path).lower() or l in f.lower():
                            lang = "telugu" if l == "telgu" else l
                            break
                if not lang:
                    logging.warning(f"Could not infer language for {f}. Skipping. Place in a language-named folder or use --language.")
                    continue
                    
                process_file(root_path / f, out_dir, lang)

if __name__ == "__main__":
    main()
