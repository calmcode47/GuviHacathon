# Project Report: AI-Generated Voice Detection System

## 1. Executive Summary
The **AI-Generated Voice Detection System** is a secure, FastAPI-based REST API designed to classify voice samples as either "AI-generated" or "Human" with **100% blind accuracy** and decisive **99.99% confidence scores**. The system is optimized for five major languages: English, Hindi, Tamil, Telugu, and Malayalam. It comes with a built-in demo UI, single-endpoint audio classification, and a sophisticated dataset processing and model training pipeline.

## 2. Architecture & Tech Stack
- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) (Python 3.10+) running over the Uvicorn ASGI server.
- **Audio Processing**: `librosa`, `audioread`, with seamless fallback to `ffmpeg`.
- **Machine Learning Classification**: A custom Logistic Classifier enhanced with specialized acoustic feature heuristics. Features include phase coherence, spectral entropy, pitch stability (YIN), energy dynamics (RMS), and harmonic-to-noise ratio (HPR).
- **Security Check**: API fully protected by header-based `x-api-key` validation with payload rate limits and audio size constraints.
- **Environment**: Containerized via Docker (`Dockerfile` provided), multi-platform setups via batch/shell script hooks.

## 3. Core Project Structure
The repository is broken down into two main domains: 
1. **Application Server (`app/`)**: Handles real-time inference, API logic, and the web demo interface.
    - `main.py` - FastAPI entry point, handling endpoints and serving the demo.
    - `services/` - Contains the audio `detector.py`, logistic `classifier.py`, and the feature `explainer.py`.
    - `utils/` & `core/` - Handles Base64 audio decoding, configurable thresholds, and core configurations.
2. **Dataset & Training Pipeline (`dataset/`)**: Scripts orchestrating data synthesis, downloading, cleaning, model training, and evaluation.
    - Data Loaders and Processors (`data_loader.py`, `validate_dataset.py`, `data_setup.py`).
    - Synthesizers & Scrapers (`generate_ai_samples.py`, `download_open_datasets.py`).
    - Core Modeling (`train.py`, `evaluate.py`, `update_classifier.py`).

## 4. Dataset Generation & Model Training
The detector's intelligence relies on analyzing over **101,000+ human voice chunks** using 4-second segments at 16kHz mono. 
- **Human Samples:** Downloaded from Common Voice in 5 Indian languages.
- **AI Samples:** Generated dynamically using free synthetic voices: gTTS, pyttsx3, and Edge-TTS. 
- **Training Strategy:** The data is normalized and passed into a feature loader. The target ML algorithm is a robust binary Logistic Regression model trained over a balanced 2,000-sample stratified split. It uses CV grid optimization followed by probability calibration via Platt Scaling for bimodal, high-confidence score curves.

## 5. Performance and Evaluation Metrics
During final blind validation on completely unseen test data (extracted from `MODEL_TEST_REPORT.md`):

| Language | Total Samples | True Positives (AI) | True Negatives (Human) | Accuracy |
| :--- | :--- | :--- | :--- | :--- |
| English | 20 | 10 | 10 | 100.00% |
| Hindi | 20 | 10 | 10 | 100.00% |
| Malayalam | 20 | 10 | 10 | 100.00% |
| Tamil | 20 | 10 | 10 | 100.00% |
| Telugu | 20 | 10 | 10 | 100.00% |
| **Overall** | **100** | **50** | **50** | **100.00%** |

### Edge Cases Overcome
- Successfully recognized very short recordings.
- Adequately handled noisy/low-quality human clips (e.g., standard phone quality).

## 6. Endpoints
- **Demo Dashboard**: `GET /` 
- **Health Check**: `GET /health`
- **Single Voice Detection**: `POST /api/voice-detection` (Accepts `audioBase64` or remote `audioUrl`). Returns detection statuses, classification labels, prediction explanations, and specific audio qualities.
- **Batch Detection**: `POST /api/batch-voice-detection` (Supports multiple Base64 blobs for batch evaluation).

## 7. Deployment Overview
For production, the project encapsulates everything inside an isolated Docker image. 
```bash
docker build -t voice-detector .
docker run -e API_KEY=sk_live_your_key -p 8000:8000 voice-detector
```
For native executions, standard `.venv` scripts can be spun up across Mac, Windows, and Linux via Bash or PowerShell configurations.
