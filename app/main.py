import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, Body
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.schemas import VoiceDetectionRequest, VoiceDetectionResponse, ErrorResponse, BatchDetectionRequest, BatchDetectionResponse, AudioQuality
from app.core.config import API_KEY, EXPECTED_AUDIO_FORMAT
from app.utils.audio import assert_supported_language, decode_base64_mp3_to_pcm
from app.utils.url_downloader import download_mp3_from_url
from app.services.detector import extract_features_pcm
from app.services.classifier import get_default_classifier, classify_features
from app.services.explainer import explain

app = FastAPI(title="AI-Generated Voice Detection API", version="1.0.0")

_templates_dir = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))


def get_api_key_from_headers(request: Request) -> Optional[str]:
    """
    Extract API key from x-api-key or Authorization: Bearer headers.
    """
    xk = request.headers.get("x-api-key")
    if xk:
        return xk
    auth = request.headers.get("authorization")
    if auth and auth.startswith("Bearer "):
        return auth[7:]
    return None


@app.get("/")
async def demo_home(request: Request):
    return templates.TemplateResponse("demo.html", {"request": request})


@app.get("/health")
async def health():
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        model_path = Path(env_path)
    else:
        model_path = Path(__file__).resolve().parents[1] / "model" / "model.json"
    return {
        "status": "ok",
        "model_loaded": model_path.exists(),
    }


@app.post("/api/voice-detection", response_model=VoiceDetectionResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    408: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
})
async def voice_detection(payload: dict = Body(...), http_request: Request = None):
    api_key = get_api_key_from_headers(http_request)
    if not api_key or api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid API key or malformed request", "code": 401})
    try:
        language = str(payload.get("language", ""))
        audio_format = str(payload.get("audioFormat", ""))
        audio_b64 = payload.get("audioBase64")
        audio_url = payload.get("audioUrl")
        assert_supported_language(language)
        if audio_format.lower() != EXPECTED_AUDIO_FORMAT:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Unsupported audio format; only mp3 is accepted", "code": 400})
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid language or audio format", "code": 400})
    if audio_b64 and audio_url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Provide either audioBase64 or audioUrl, not both", "code": 400})
    if not audio_b64 and not audio_url:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Must provide either audioBase64 or audioUrl", "code": 400})
    if audio_url:
        try:
            audio_b64 = download_mp3_from_url(audio_url)
        except ValueError as ve:
            msg = str(ve)
            if "exceeds 50mb" in msg.lower() or "too large" in msg.lower():
                return JSONResponse(status_code=413, content={"status": "error", "message": msg, "code": 413})
            return JSONResponse(status_code=400, content={"status": "error", "message": msg, "code": 400})
        except TimeoutError as te:
            return JSONResponse(status_code=408, content={"status": "error", "message": str(te), "code": 408})
        except Exception as e:
            return JSONResponse(status_code=500, content={"status": "error", "message": f"Download failed: {str(e)}", "code": 500})
    try:
        pcm = decode_base64_mp3_to_pcm(str(audio_b64 or ""))
        feats = extract_features_pcm(pcm)
        model = get_default_classifier()
        label, confidence, _ = classify_features(feats, pcm, model)
        explanation = explain(feats, model, label)
        aq = AudioQuality(
            formatValid=bool(pcm.format_valid),
            sampleRateSuspect=bool(pcm.sample_rate_suspect),
            shortAudio=bool(pcm.short_audio),
            durationSeconds=float(pcm.duration_seconds),
            sampleRate=int(pcm.sample_rate),
            channels=int(pcm.channels),
        )
        return VoiceDetectionResponse(
            status="success",
            language=language,
            classification=label,
            confidenceScore=round(float(confidence), 4),
            explanation=explanation,
            audioQuality=aq,
        )
    except ValueError as ve:
        msg = str(ve)
        if "too large" in msg.lower():
            return JSONResponse(status_code=413, content={"status": "error", "message": msg, "code": 413})
        return JSONResponse(status_code=400, content={"status": "error", "message": msg, "code": 400})
    except Exception:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to analyze audio", "code": 500})


@app.post("/api/batch-voice-detection", response_model=BatchDetectionResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
})
async def batch_voice_detection(request: BatchDetectionRequest, x_api_key: str = ""):
    # API Key validation
    if not x_api_key or x_api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid API key or malformed request", "code": 401})

    results = []
    model = get_default_classifier()
    
    for i, audio_request in enumerate(request.audio_samples):
        try:
            # Input validation
            assert_supported_language(audio_request.language)
            if audio_request.audioFormat.lower() != EXPECTED_AUDIO_FORMAT:
                results.append({
                    "index": i,
                    "status": "error",
                    "message": "Unsupported audio format; only mp3 is accepted"
                })
                continue

            pcm = decode_base64_mp3_to_pcm(audio_request.audioBase64)
            feats = extract_features_pcm(pcm)
            label, conf, _ = classify_features(feats, pcm, model)
            explanation = explain(feats, model, label)

            results.append({
                "index": i,
                "status": "success",
                "language": audio_request.language,
                "classification": label,
                "confidenceScore": round(float(conf), 4),
                "explanation": explanation,
            })
        except ValueError as ve:
            results.append({
                "index": i,
                "status": "error",
                "message": str(ve)
            })
        except Exception:
            results.append({
                "index": i,
                "status": "error",
                "message": "Failed to analyze audio"
            })

    return BatchDetectionResponse(
        status="success",
        total_samples=len(request.audio_samples),
        results=results,
    )
