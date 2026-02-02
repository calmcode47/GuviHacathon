from fastapi import FastAPI, Header
from fastapi.responses import JSONResponse

from app.models.schemas import VoiceDetectionRequest, VoiceDetectionResponse, ErrorResponse
from app.core.config import API_KEY, EXPECTED_AUDIO_FORMAT
from app.utils.audio import assert_supported_language, decode_base64_to_temp_mp3, load_audio_waveform, cleanup_temp_file
from app.services.detector import extract_features, classify

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

    temp_path = None
    try:
        temp_path = decode_base64_to_temp_mp3(request.audioBase64)
        y, sr = load_audio_waveform(temp_path)
        feats = extract_features(y, sr)
        classification, confidence, explanation = classify(feats)

        return VoiceDetectionResponse(
            status="success",
            language=request.language,
            classification=classification,
            confidenceScore=round(float(confidence), 4),
            explanation=explanation,
        )
    except ValueError as ve:
        # Validation or input-related errors
        return JSONResponse(status_code=400, content={"status": "error", "message": str(ve)})
    except RuntimeError as re:
        # Decoding fallback failure
        return JSONResponse(status_code=500, content={"status": "error", "message": str(re)})
    except Exception:
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to analyze audio"})
    finally:
        if temp_path:
            cleanup_temp_file(temp_path)