# Dataset Workflow

- Setup directories and metadata template:
  - `python dataset/data_setup.py --base-dir data`
- Provide or review sentence corpora:
  - Files in `dataset/corpus/*.txt` with 50+ sentences per language.
- Generate AI samples:
  - `python dataset/generate_ai_samples.py --base-dir data --corpus-dir dataset/corpus --samples-per-language 50 --target-sample-rate 22050`
- Validate dataset and create split recommendations:
  - `python dataset/validate_dataset.py --base-dir data --report-csv dataset/validation_report.csv --splits-csv dataset/split_recommendations.csv`

## Open Dataset Download (Human)
- Common Voice downloader:
  - `python dataset/download_open_datasets.py --base-dir data --max-per-language 100`
- Downloads human speech for Tamil, English, Hindi, Malayalam, Telugu, saves MP3s to `data/human/{language}`, and appends metadata with checksum.
- Notes include dataset version for traceability.

## Notes
- Free TTS only: gTTS, pyttsx3, Edge-TTS.
- MP3 output at 16–44.1 kHz; default 22.05 kHz.
- Deterministic generation: round‑robin engines; fallback to gTTS on errors.
- Metadata appended to `data/metadata.csv`.
- Progress bars and logging included for all steps.

## Human Voice Collection
- See `dataset/collect_human_voices.md` for recording instructions, consent template, and file naming convention.

## Requirements
- Python 3.8+
- Install:
  - `pip install -r requirements.txt`
  - Ensure FFmpeg is installed and available in PATH for MP3 export when needed.
