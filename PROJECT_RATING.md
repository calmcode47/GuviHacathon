# Fake Audio Detection AI Prototype — Project Rating

**Overall rating: 7.2 / 10** — Solid prototype with clear scope, good structure, and production-ready API; held back by current model performance and small dataset.

---

## 1. Concept & Scope (8/10)

- **Clear problem**: AI-generated vs human voice detection in multiple Indian languages (Tamil, English, Hindi, Malayalam, Telugu).
- **Sensible approach**: Handcrafted acoustic features (pitch, jitter, HNR, spectral, phase, prosody) + logistic regression — interpretable and lightweight.
- **Multilingual**: Explicit language support and metadata (e.g. `metadata.csv`) with TTS engines (gTTS, Edge-TTS, pyttsx3) for AI samples.

**Gaps**: No deep-learning baseline (e.g. small CNN/embedding model) for comparison; “fake” is limited to TTS-style synthesis, not full deepfake clones.

---

## 2. Codebase & Architecture (8/10)

**Strengths**

- **Separation of concerns**: `app/` (API, detector, classifier, explainer, audio utils), `dataset/` (data prep, training, evaluation), `tests/`.
- **API design**: FastAPI with Pydantic schemas, API-key auth, single and batch detection, clear error responses (400/401/500).
- **Config**: Language set, audio format (MP3), size/duration limits, API key via env; no hardcoded secrets in repo.
- **Explainability**: Explainer ties model weights to human/AI phrases — good for a prototype and trust.

**Issues**

- **Feature list mismatch**: `dataset/train_model.py` uses **9** features (no `spectral_rolloff_median`); `data_loader.py` and `app/services/classifier.py` use **10**. Training with `train_model.py` and exporting to `model.json` can misalign features. **Recommendation**: Single shared `FEATURE_NAMES` (e.g. in `app/services/detector` or a shared constants module).
- **Demo app wiring**: `app/demo.py` is a separate FastAPI app that only serves the HTML template; it does not mount the detection API. The template calls `/api/voice-detection`, so either mount the main app routes in `demo.py` or run the main app and point the demo at it.
- **Duplicate assets**: `demo.html` exists in both `app/templates/` and project root; `classifier.py.bak` should be removed or ignored.

---

## 3. Data Pipeline (7.5/10)

**Strengths**

- **Structured data**: `data/ai/{lang}/`, `data/human/{lang}/`, `data/human/real/`, plus `metadata.csv` with clip_id, language, source_type, TTS engine, checksum.
- **Reproducibility**: Corpus-driven AI generation, round-robin TTS engines, optional caching (`data/cache/features.npz`).
- **Scripts**: `generate_ai_samples.py`, `normalize_human_samples.py`, `validate_dataset.py`, `download_open_datasets.py`, `collect_human_voices.md` — good for onboarding and extension.

**Gaps**

- **Scale**: ~10 samples per language per source (e.g. 10 AI + 10 human per language) is very small; evaluation and training reports show this (e.g. validation splits of 2–4 samples).
- **Balance**: Training reports show heavy class bias (e.g. confusion matrix `[[0, 10], [0, 10]]` — all predicted as one class), so more human data and balanced sampling are needed.

---

## 4. Model & Features (7/10)

**Strengths**

- **Feature set**: Pitch variance, jitter proxy, HNR, spectral flatness/rolloff, phase coherence, energy entropy, temporal discontinuity, pause std, voiced ratio — all relevant to TTS vs human.
- **Detector**: Uses `librosa` (YIN f0, HPSS, spectral, onset), handles multi-channel by aggregating (e.g. median), and exposes extra stats (_iqr, _p05, _p95) for possible future use.
- **Classifier**: Standardized features, logistic regression, optional Platt scaling (`calib_a`, `calib_b`), reliability adjustment for short/suspect audio.
- **Confidence logic**: BORDERLINE for low confidence, which is good for UX.

**Issues**

- **Current model**: `app/model/model.json` is the **default zero-weight model** (all weights 0, bias 0, calib 0). So the API runs but predictions are effectively uncalibrated.
- **Training outputs**: `training_out/report.json` and `training_out_enhanced/report.json` show accuracy and ROC-AUC at **0.5** (random) and full prediction to one class — consistent with tiny, imbalanced data.
- **Export path**: `dataset/export_weights_to_json.py` writes to `app/model/model.json` from `training_out/weights.pkl`; after proper training, running this would deploy a real model. Currently, the deployed JSON is not from that pipeline.

---

## 5. API & Integration (8.5/10)

**Strengths**

- **Endpoints**: `GET /health`, `POST /api/voice-detection`, `POST /api/batch-voice-detection` with clear request/response schemas.
- **Input validation**: Language allowlist, MP3-only, base64 decode, max bytes/duration; temp file cleanup after decode.
- **Audio decoding**: Audioread + ffmpeg fallback for MP3 → PCM; `PCMDecodeResult` carries format/sample-rate/short-audio flags for reliability scoring.
- **Tests**: `test_health.py` and `test_voice_detection.py` (success + invalid API key) with TestClient.

**Gaps**

- **Demo**: As above, demo HTML expects `/api/voice-detection` but `demo.py` does not include those routes; either integrate with main app or document the correct URL (e.g. main app on port 8000).
- **API key**: Default `sk_test_123456789` and demo uses `sk_test_key` — ensure production uses env and docs warn against default keys.

---

## 6. Evaluation & Reproducibility (7/10)

**Strengths**

- **Evaluation script**: `dataset/evaluate.py` — accuracy, precision, recall, F1, ROC-AUC, ECE, confusion matrix, ROC curve, calibration plot, feature importance.
- **Train/val/test**: `train.py` uses `VoiceDataset`, stratified splits, optional balancing, GridSearchCV for C, Platt calibration.
- **Artifacts**: `evaluation_out/` (metrics.json, PDFs), `training_out/` (report.json, weights.pkl).

**Gaps**

- **Metrics**: Current metrics (e.g. accuracy 0.5, ROC-AUC 0.5) reflect data size and imbalance, not pipeline bugs.
- **Reproducibility**: No single `README` that ties: (1) data setup, (2) train with `train.py` or `train_model.py`, (3) export weights to `app/model/model.json`, (4) run API and demo. A short “Quick start” would help.

---

## 7. Security & Robustness (7.5/10)

- **API key**: Required for detection endpoints; 401 on invalid key.
- **Limits**: `MAX_AUDIO_BYTES`, `MAX_DURATION_SECONDS` to avoid abuse.
- **Input checks**: Base64 validation, MP3 header check, duration after decode.
- **Reliability**: Confidence reduced for short or suspect sample rate — good for transparent behavior.

**Recommendation**: Add rate limiting and optional request logging for production.

---

## Summary Table

| Area                 | Score | Notes                                                |
|----------------------|-------|------------------------------------------------------|
| Concept & scope      | 8.0   | Clear, multilingual, interpretable pipeline         |
| Codebase & architecture | 8.0 | Clean layout; fix feature list and demo wiring       |
| Data pipeline        | 7.5   | Good structure; needs more and balanced data         |
| Model & features     | 7.0   | Strong feature set; deployed model is untrained      |
| API & integration    | 8.5   | Production-ready API; demo routing to be fixed       |
| Evaluation           | 7.0   | Solid scripts; current metrics reflect data limits   |
| Security & robustness| 7.5   | Sensible guards; add rate limiting for production    |

---

## Top 5 Recommendations

1. **Align feature lists**: Use one canonical `FEATURE_NAMES` (include `spectral_rolloff_median`) in `train_model.py`, `data_loader.py`, and classifier so training and inference always match.
2. **Train and deploy a real model**: Add more human/AI samples (e.g. 100+ per class per language), balance classes, run `dataset/train.py`, then `dataset/export_weights_to_json.py` and copy the result to `app/model/model.json`.
3. **Wire demo to API**: Either mount main app routes in `app/demo.py` or serve the same app with the demo template and document which URL to use.
4. **Single README**: Add a “Quick start” that covers: data setup → train → export → run API/demo, and note the difference between `train.py` (10 features, recommended) and `train_model.py` (9 features).
5. **Expand data**: Use `download_open_datasets.py` and more TTS generations so validation splits are meaningful and metrics (accuracy, AUC) can exceed random.

---

**Verdict**: This is a **strong prototype** for a fake (TTS) audio detection system: clear design, good API, interpretable features, and explainability. With a single feature-list source, a properly trained model deployed to `app/model/model.json`, demo wired to the detection API, and more balanced data, it would be a **8+** and ready for internal or hackathon demos.

---

## Updates applied (post-rating)

- **Shared feature list**: `app/core/features.py` defines `FEATURE_NAMES` (10 features including `spectral_rolloff_median`). Used by `classifier.py`, `data_loader.py`, `train_model.py`, and training/eval.
- **Demo wired to API**: `GET /` in `app/main.py` serves the demo template; same app handles `/api/voice-detection`. Default API key set to `sk_test_key` for local/demo. `app/demo.py` now runs the main app on port 8000.
- **Trained model**: `app/model/model.json` is populated via `train_model.py` (e.g. `--max-per-class 15` for a quick 30-sample train). Full training: run `train_model.py` without `--max-per-class` or use `dataset/train.py` with `--refresh-cache` after growing data.
- **README Quick start**: End-to-end steps (data → train → export → run) and demo/API key notes added at the top of `README.md`.
- **Dataset growth**: `generate_ai_samples.py` can be run with `--samples-per-language 50`; partial runs added more AI samples (e.g. 50 English, 37 Tamil, 29 Hindi). Use `--max-per-class` in `train_model.py` for quick iteration; remove it for full-data training.
