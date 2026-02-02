from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from app.models.schemas import VoiceDetectionRequest, VoiceDetectionResponse, ErrorResponse
from app.core.config import API_KEY, EXPECTED_AUDIO_FORMAT
from app.utils.audio import assert_supported_language, decode_base64_mp3_to_pcm
from app.services.detector import extract_features_pcm
from app.services.classifier import get_default_classifier, classify_features
from app.services.explainer import explain

app = FastAPI(title="AI-Generated Voice Detection API", version="1.0.0")


@app.post("/api/voice-detection", response_model=VoiceDetectionResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
})
async def voice_detection(request: VoiceDetectionRequest, x_api_key: str = Header(default="")):
    # API Key validation
    if not x_api_key or x_api_key != API_KEY:
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid API key or malformed request"})

    # Input validation
    try:
        assert_supported_language(request.language)
        if request.audioFormat.lower() != EXPECTED_AUDIO_FORMAT:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Unsupported audio format; only mp3 is accepted"})
    except Exception:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid language or audio format"})

    try:
        pcm = decode_base64_mp3_to_pcm(request.audioBase64)
        feats = extract_features_pcm(pcm)
        model = get_default_classifier()
        label, confidence, _ = classify_features(feats, pcm, model)
        explanation = explain(feats, model, label)

        return VoiceDetectionResponse(
            status="success",
            language=request.language,
            classification=label,
            confidenceScore=round(float(confidence), 4),
            explanation=explanation,
        )
    except ValueError as ve:
        # Validation or input-related errors
        return JSONResponse(status_code=400, content={"status": "error", "message": str(ve)})
    except Exception:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to analyze audio"})
