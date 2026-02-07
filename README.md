# AI-Generated Voice Detection API (Tamil, English, Hindi, Malayalam, Telugu)

A secure FastAPI-based REST API that accepts a Base64-encoded MP3 voice sample and classifies whether the voice is AI-generated or Human. Supports five languages: Tamil, English, Hindi, Malayalam, and Telugu.

## Quick start (end-to-end)

Run the app with the demo UI and a trained model in a few steps:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. (Optional) Data setup — if you don't have data/ yet
python dataset/data_setup.py --base-dir data
# Generate AI samples (uses corpus in dataset/corpus/)
python dataset/generate_ai_samples.py --base-dir data --corpus-dir dataset/corpus --samples-per-language 50

# 3. Train a model (use --max-per-class 15 for a quick 30-sample train)
PYTHONPATH=. python dataset/train_model.py --base-dir data --output app/model/model.json --max-per-class 15
# Or train on full data (no cap):
# PYTHONPATH=. python dataset/train_model.py --base-dir data --output app/model/model.json

# 4. Run the API and demo
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Or: python -m app.demo
```

- **Demo UI**: Open **http://localhost:8000/** — upload an MP3 and run detection.
- **API key (local)**: Use `x-api-key: sk_test_key` (or set `API_KEY` in the environment).
- **Docs**: http://localhost:8000/docs

## Features
- **Demo UI** at `GET /` (upload MP3, get AI vs Human result).
- Single endpoint: `POST /api/voice-detection`
- Request JSON contains: `language`, `audioFormat`, `audioBase64`
- Validates header `x-api-key`
- Returns JSON with `classification` (AI_GENERATED or HUMAN), `confidenceScore` (0.0–1.0), and `explanation`
- Lightweight heuristic analysis using audio features (no external detection APIs)
- Cross-platform: macOS, Windows, Linux via Docker

## Minimal Local Run (Summary)

- **Docker (recommended, cross-platform)**:
  - Build: `docker build -t voice-detector .`
  - Run: `docker run -e API_KEY=sk_live_your_key -p 8000:8000 voice-detector`
- **Native Python (macOS/Windows)**:
  - Create venv (Python 3.10+), activate it.
  - Install deps: `pip install -r requirements.txt`
  - Set `API_KEY` in your shell.
  - Start server: `uvicorn app.main:app --host 0.0.0.0 --port 8000`

## Quick Start (Docker)
This is the easiest way to run locally and across platforms.

```bash
# From the repo root
docker build -t voice-detector .
# Override API key if desired
docker run -e API_KEY=sk_live_your_key -p 8000:8000 voice-detector
```

### Test with cURL
```bash
curl -X POST "http://localhost:8000/api/voice-detection" \
  -H "Content-Type: application/json" \
  -H "x-api-key: sk_live_your_key" \
  -d '{
    "language": "Tamil",
    "audioFormat": "mp3",
    "audioBase64": "<YOUR_BASE64_MP3>"
  }'
```

## Quick Start (Python)
Requirements: Python 3.10+.

```bash
# Create venv
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Optional: set API key (default for local: sk_test_key)
export API_KEY=sk_test_key   # or sk_live_your_key in production

# Run server
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Note: For MP3 decoding, `librosa` uses `audioread` which may rely on `ffmpeg` or system codecs. If MP3 fails on your system, prefer Docker or install `ffmpeg` locally.

## Environment Setup Scripts
- macOS/Linux:
```bash
bash scripts/setup_env.sh
source .venv/bin/activate
```
- Windows PowerShell:
```powershell
pwsh scripts/setup_env.ps1
. .venv\Scripts\Activate.ps1
```
- Windows cmd:
```bat
scripts\setup_env.bat
.venv\Scripts\activate.bat
```

## Endpoint Details
- Method: `POST`
- Path: `/api/voice-detection`
- Headers: either `x-api-key: <YOUR_SECRET_API_KEY>` or `Authorization: Bearer <YOUR_SECRET_API_KEY>`
- Body (JSON) — provide exactly one of `audioBase64` or `audioUrl`:
```json
{
  "language": "Tamil | English | Hindi | Malayalam | Telugu",
  "audioFormat": "mp3",
  "audioBase64": "<Base64-encoded MP3>",
  "audioUrl": "https://example.com/path/to/file.mp3"
}
```

### Success Response Example
```json
{
  "status": "success",
  "language": "Tamil",
  "classification": "AI_GENERATED",
  "confidenceScore": 0.91,
  "explanation": "Unnatural pitch stability and clean harmonic profile detected",
  "audioQuality": {
    "formatValid": true,
    "sampleRateSuspect": false,
    "shortAudio": false,
    "durationSeconds": 12.34,
    "sampleRate": 22050,
    "channels": 1
  }
}
```

### Error Response Example
```json
{
  "status": "error",
  "message": "Invalid API key or malformed request"
}
```

## Health & API Documentation

- **Health check**: `GET /health`
  - Returns `{"status": "ok", "model_loaded": true/false}`.
  - Useful for readiness probes and simple monitoring.
- **Interactive docs** (FastAPI built-in):
  - Open `http://localhost:8000/docs` for Swagger UI.
  - Open `http://localhost:8000/redoc` for ReDoc.

## Design Notes
- Heuristic features: pitch stability (YIN), energy dynamics (RMS), spectral flatness, MFCC temporal variance, harmonic-to-noise ratio (HPR), onset rate.
- AI voices often have unusually consistent pitch and energy, lower jitter, higher harmonic-to-noise ratios, and stable MFCCs.
- Humans typically show more micro-variations (jitter/shimmer), irregular energy changes, and breath/noise.

## Project Structure
```
app/
  main.py              # FastAPI app, demo at /, API at /api/*
  core/config.py       # Config and constants
  models/schemas.py    # Pydantic request/response models
  utils/audio.py       # Base64 decoding, MP3 load helpers (ffmpeg fallback)
  services/detector.py # Feature extraction & classification logic
  services/classifier.py # Logistic classifier with model auto-load or embedded weights
  services/explainer.py  # Deterministic explanation from feature contributions

dataset/
  README.md                  # Dataset workflow overview
  data_setup.py              # Create data/{human,ai}/{language}/ structure
  download_open_datasets.py  # Fetch open human speech (Common Voice) per language
  generate_ai_samples.py     # Create AI voices via gTTS, Edge-TTS, pyttsx3
  validate_dataset.py        # Validate MP3s and recommend train/val/test splits
  normalize_human_samples.py # Normalize filenames and append metadata
  data_loader.py             # Load/caches features; balanced stratified splits
  train.py                   # Train logistic model with CV grid + calibration
  evaluate.py                # Evaluate metrics, ECE, and export plots
  update_classifier.py       # Embed trained weights into runtime classifier
  setup_data.sh              # One-shot data creation/generation/validation
```

## Security
- API protected by `x-api-key` header.
- The default key in Docker is for local testing only; override in deployment.

## Advanced Decoding & Validation
- Primary decode: `librosa` via `audioread` (uses `ffmpeg` if available).
- Fallback: If primary decode fails, transcode MP3 to WAV via `ffmpeg` then analyze.
- Lightweight MP3 header validation (ID3 or MPEG frame sync).
- Input guardrails (configurable via env):
  - `MAX_AUDIO_BYTES` (default `10 * 1024 * 1024`) — rejects oversized inputs.
  - `MAX_DURATION_SECONDS` (default `60`) — rejects overly long audio to ensure responsiveness.

## Configuration
- Environment variables:
  - `API_KEY` — required header `x-api-key` must match.
  - `MAX_AUDIO_BYTES` — optional; adjust allowed Base64-decoded size.
  - `MAX_DURATION_SECONDS` — optional; adjust allowed duration.
- OS setup for native runs:
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - Windows: install FFmpeg and add to `PATH`.

## Troubleshooting on Windows/macOS

- **Verify ffmpeg is available**:
  - Run `ffmpeg -version` in your terminal or PowerShell.
  - If the command is not found, install ffmpeg as described above and restart your shell.
- **When MP3 decode fails**:
  - The API first tries native decoders (`audioread`/`librosa`).
  - On failure, it falls back to ffmpeg and logs a warning like: *\"Primary MP3 decode failed; attempting ffmpeg fallback\"*.
  - If ffmpeg is missing, a clear error is logged and the request fails with a 500 status.
- If you run into codec issues or platform-specific audio errors, use the Docker flow, which bundles ffmpeg and a known-good environment.

## Notes
- Input audio is decoded for analysis only; the original content is not modified.
- Language field is validated to be one of the five supported languages.
- No hard-coded results; classification is determined by computed features.

## Dataset & Training
- Training dependencies:
  - pip install -r requirements_training.txt
- Create directories and metadata:
  - python dataset/data_setup.py --base-dir data
- Download open human speech (requires a Hugging Face token):
  - Set token in shell: $Env:HF_TOKEN="hf_xxx"
  - python dataset/download_open_datasets.py --base-dir data --max-per-language 60 --versions 13_0 11_0 9_0 7_0
- Generate AI voices:
  - python dataset/generate_ai_samples.py --base-dir data --corpus-dir dataset/corpus --samples-per-language 50 --target-sample-rate 22050
- Validate dataset:
  - python dataset/validate_dataset.py --base-dir data --report-csv dataset/validation_report.csv --splits-csv dataset/split_recommendations.csv
- Cache features and splits:
  - python dataset/data_loader.py --data-dir data --val-split 0.2 --test-split 0.0 --random-seed 42 --balance
- Train with CV grid and calibration:
  - python dataset/train.py --data-dir data --output-dir training_out --val-split 0.2 --random-seed 42
- Evaluate:
  - python dataset/evaluate.py --data-dir data --weights training_out/weights.pkl --random-seed 42 --output-dir evaluation_out
- Update runtime classifier:
  - python dataset/update_classifier.py --weights training_out/weights.pkl --classifier-path app/services/classifier.py
- Deploy trained model to the API:
  - `python dataset/export_weights_to_json.py --weights training_out/weights.pkl --output app/model/model.json`
  - Or train directly to app model: `PYTHONPATH=. python dataset/train_model.py --base-dir data --output app/model/model.json [--max-per-class 15]`
- Alternative runtime load:
  - Place a JSON model at app/model/model.json or set MODEL_PATH; the API auto-loads this file if present.

## Sample Client Script

- A simple cross-platform CLI client is provided at `scripts/upload_mp3_to_api.py`.
- Example usage:
  ```bash
  python scripts/upload_mp3_to_api.py \
    --file path/to/sample.mp3 \
    --language Tamil \
    --api-key sk_live_your_key \
    --url http://localhost:8000/api/voice-detection
  ```

See TRAINING.md for a concise guide with commands and outputs.

## Sample Base64
For testing, convert an MP3 file to Base64:
```bash
base64 -i sample.mp3 > sample.b64
```
Then paste the contents into `audioBase64`.

## Deploying
- Use Docker container in any environment supporting containers.
- For cloud, run behind HTTPS; this repo provides the API app only.
