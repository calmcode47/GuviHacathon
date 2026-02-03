import os
from pathlib import Path
import logging
import time
from typing import Dict

from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

from app.models.schemas import (
    VoiceDetectionRequest, VoiceDetectionResponse, ErrorResponse,
    BatchVoiceDetectionRequest, BatchVoiceDetectionResponse, AudioQualityMetrics
)
from app.core.config import API_KEY, EXPECTED_AUDIO_FORMAT, HIGH_CONFIDENCE_THRESHOLD, BORDERLINE_MIN_CONFIDENCE
from app.utils.audio import assert_supported_language, decode_base64_mp3_to_pcm
from app.services.detector import extract_features_pcm
from app.services.classifier import get_default_classifier, classify_features
from app.services.explainer import explain
from app.services.audio_quality import assess_audio_quality

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
if not SLOWAPI_AVAILABLE:
    logger.warning("slowapi not installed, rate limiting disabled")

# Initialize rate limiter if available
if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app = FastAPI(title="AI-Generated Voice Detection API", version="1.0.0")
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
else:
    limiter = None
    app = FastAPI(title="AI-Generated Voice Detection API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response

# Request timing middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Cache the classifier model at startup
_classifier_cache = None

@app.on_event("startup")
async def startup_event():
    """Load and cache the classifier model at startup for faster response times."""
    global _classifier_cache
    logger.info("Loading classifier model...")
    _classifier_cache = get_default_classifier()
    logger.info("Classifier model loaded and cached")


@app.get("/health")
async def health():
    """Lightweight health check endpoint."""
    env_path = os.getenv("MODEL_PATH")
    if env_path:
        model_path = Path(env_path)
    else:
        model_path = Path(__file__).resolve().parents[1] / "model" / "model.json"
    return {
        "status": "ok",
        "model_loaded": model_path.exists(),
    }


def rate_limit_decorator(func):
    """Apply rate limiting if available, otherwise pass through."""
    if SLOWAPI_AVAILABLE and limiter:
        return limiter.limit("10/minute")(func)
    return func

@app.post("/api/voice-detection", response_model=VoiceDetectionResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
})
@rate_limit_decorator
async def voice_detection(request: Request, voice_request: VoiceDetectionRequest, x_api_key: str = Header(default="")):
    # API Key validation
    if not x_api_key or x_api_key != API_KEY:
        logger.warning("Invalid API key attempt")
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid API key or malformed request"})

    # Input validation
    try:
        assert_supported_language(voice_request.language)
        if voice_request.audioFormat.lower() != EXPECTED_AUDIO_FORMAT:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Unsupported audio format; only mp3 is accepted"})
    except Exception as e:
        logger.warning(f"Invalid input: {e}")
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid language or audio format"})

    try:
        # Use cached model for faster response
        model = _classifier_cache if _classifier_cache else get_default_classifier()
        
        pcm = decode_base64_mp3_to_pcm(voice_request.audioBase64)
        feats = extract_features_pcm(pcm)
        label, confidence, p_ai = classify_features(feats, pcm, model)
        explanation = explain(feats, model, label)
        if BORDERLINE_MIN_CONFIDENCE <= confidence < HIGH_CONFIDENCE_THRESHOLD:
            explanation = "Borderline case; " + explanation

        # Add confidence threshold handling for borderline cases
        confidence_category = "high"
        if confidence < 0.6:
            confidence_category = "low"
        elif confidence < 0.8:
            confidence_category = "medium"

        # Assess audio quality
        quality_metrics = assess_audio_quality(pcm)
        audio_quality = AudioQualityMetrics(
            sampleRate=quality_metrics["sampleRate"],
            duration=quality_metrics["duration"],
            channels=quality_metrics["channels"],
            isValidFormat=quality_metrics["isValidFormat"],
            qualityScore=quality_metrics["qualityScore"]
        )

        return VoiceDetectionResponse(
            status="success",
            language=voice_request.language,
            classification=label,
            confidenceScore=round(float(confidence), 4),
            confidenceCategory=confidence_category,
            explanation=explanation,
            audioQuality=audio_quality,
        )
    except ValueError as ve:
        # Validation or input-related errors
        logger.warning(f"Validation error: {ve}")
        return JSONResponse(status_code=400, content={"status": "error", "message": str(ve)})
    except Exception as e:
        logger.exception("Failed to analyze audio")
        return JSONResponse(status_code=500, content={"status": "error", "message": "Failed to analyze audio"})


def batch_rate_limit_decorator(func):
    """Apply rate limiting if available, otherwise pass through."""
    if SLOWAPI_AVAILABLE and limiter:
        return limiter.limit("5/minute")(func)
    return func

@app.post("/api/voice-detection/batch", response_model=BatchVoiceDetectionResponse, responses={
    400: {"model": ErrorResponse},
    401: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
})
@batch_rate_limit_decorator
async def batch_voice_detection(request: Request, batch_request: BatchVoiceDetectionRequest, x_api_key: str = Header(default="")):
    """Batch process multiple audio samples."""
    # API Key validation
    if not x_api_key or x_api_key != API_KEY:
        logger.warning("Invalid API key attempt for batch endpoint")
        return JSONResponse(status_code=401, content={"status": "error", "message": "Invalid API key or malformed request"})

    # Use cached model for faster response
    model = _classifier_cache if _classifier_cache else get_default_classifier()
    
    results = []
    failed_count = 0
    
    for sample in batch_request.samples:
        try:
            # Input validation
            assert_supported_language(sample.language)
            if sample.audioFormat.lower() != EXPECTED_AUDIO_FORMAT:
                failed_count += 1
                continue
            
            pcm = decode_base64_mp3_to_pcm(sample.audioBase64)
            feats = extract_features_pcm(pcm)
            label, confidence, p_ai = classify_features(feats, pcm, model)
            explanation = explain(feats, model, label)
            if BORDERLINE_MIN_CONFIDENCE <= confidence < HIGH_CONFIDENCE_THRESHOLD:
                explanation = "Borderline case; " + explanation

            # Confidence category
            confidence_category = "high"
            if confidence < 0.6:
                confidence_category = "low"
            elif confidence < 0.8:
                confidence_category = "medium"

            # Assess audio quality
            quality_metrics = assess_audio_quality(pcm)
            audio_quality = AudioQualityMetrics(
                sampleRate=quality_metrics["sampleRate"],
                duration=quality_metrics["duration"],
                channels=quality_metrics["channels"],
                isValidFormat=quality_metrics["isValidFormat"],
                qualityScore=quality_metrics["qualityScore"]
            )

            results.append(VoiceDetectionResponse(
                status="success",
                language=sample.language,
                classification=label,
                confidenceScore=round(float(confidence), 4),
                confidenceCategory=confidence_category,
                explanation=explanation,
                audioQuality=audio_quality,
            ))
        except Exception as e:
            logger.warning(f"Failed to process sample in batch: {e}")
            failed_count += 1
    
    return BatchVoiceDetectionResponse(
        status="success",
        results=results,
        totalProcessed=len(results),
        totalFailed=failed_count,
    )


@app.get("/", response_class=HTMLResponse)
async def demo_interface():
    """Demo web interface for testing the API."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Voice Detection Demo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
        }
        .container {
            background: white;
            border-radius: 20px;
            padding: 40px;
            max-width: 800px;
            width: 100%;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            margin-bottom: 10px;
            font-size: 2.5em;
        }
        .subtitle {
            color: #666;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        select, input[type="file"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        select:focus, input[type="file"]:focus {
            outline: none;
            border-color: #667eea;
        }
        button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            width: 100%;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.4);
        }
        button:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        .result {
            margin-top: 30px;
            padding: 20px;
            border-radius: 12px;
            display: none;
        }
        .result.show {
            display: block;
        }
        .result.success {
            background: #d4edda;
            border: 2px solid #28a745;
        }
        .result.error {
            background: #f8d7da;
            border: 2px solid #dc3545;
        }
        .result h3 {
            margin-bottom: 15px;
            color: #333;
        }
        .result-item {
            margin: 10px 0;
            padding: 10px;
            background: white;
            border-radius: 6px;
        }
        .confidence-bar {
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 10px 0;
            position: relative;
        }
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #28a745, #20c997);
            transition: width 0.5s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }
        .confidence-fill.low {
            background: linear-gradient(90deg, #ffc107, #ff9800);
        }
        .confidence-fill.medium {
            background: linear-gradient(90deg, #ff9800, #ff5722);
        }
        .loading {
            display: none;
            text-align: center;
            margin: 20px 0;
        }
        .loading.show {
            display: block;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎤 AI Voice Detection</h1>
        <p class="subtitle">Upload an MP3 audio file to detect if it's AI-generated or human</p>
        
        <form id="detectionForm">
            <div class="form-group">
                <label for="language">Language:</label>
                <select id="language" required>
                    <option value="English">English</option>
                    <option value="Tamil">Tamil</option>
                    <option value="Hindi">Hindi</option>
                    <option value="Malayalam">Malayalam</option>
                    <option value="Telugu">Telugu</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="audioFile">Audio File (MP3):</label>
                <input type="file" id="audioFile" accept=".mp3,audio/mpeg" required>
            </div>
            
            <button type="submit" id="submitBtn">Analyze Audio</button>
        </form>
        
        <div class="loading" id="loading">
            <div class="spinner"></div>
            <p>Analyzing audio...</p>
        </div>
        
        <div class="result" id="result">
            <h3 id="resultTitle"></h3>
            <div id="resultContent"></div>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('detectionForm');
        const loading = document.getElementById('loading');
        const result = document.getElementById('result');
        const submitBtn = document.getElementById('submitBtn');
        
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const fileInput = document.getElementById('audioFile');
            const language = document.getElementById('language').value;
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select an audio file');
                return;
            }
            
            // Convert file to base64
            const reader = new FileReader();
            reader.onload = async (event) => {
                const base64 = event.target.result.split(',')[1];
                
                // Show loading
                loading.classList.add('show');
                result.classList.remove('show');
                submitBtn.disabled = true;
                
                try {
                    const response = await fetch('/api/voice-detection', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'x-api-key': 'sk_test_123456789'
                        },
                        body: JSON.stringify({
                            language: language,
                            audioFormat: 'mp3',
                            audioBase64: base64
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (data.status === 'success') {
                        showSuccess(data);
                    } else {
                        showError(data.message || 'Analysis failed');
                    }
                } catch (error) {
                    showError('Error: ' + error.message);
                } finally {
                    loading.classList.remove('show');
                    submitBtn.disabled = false;
                }
            };
            
            reader.readAsDataURL(file);
        });
        
        function showSuccess(data) {
            result.className = 'result success show';
            document.getElementById('resultTitle').textContent = 'Analysis Result';
            
            const confidencePercent = (data.confidenceScore * 100).toFixed(1);
            const confidenceClass = data.confidenceCategory;
            
            document.getElementById('resultContent').innerHTML = `
                <div class="result-item">
                    <strong>Classification:</strong> ${data.classification === 'AI_GENERATED' ? '🤖 AI Generated' : '👤 Human'}
                </div>
                <div class="result-item">
                    <strong>Confidence:</strong> ${confidencePercent}%
                    <div class="confidence-bar">
                        <div class="confidence-fill ${confidenceClass}" style="width: ${confidencePercent}%">
                            ${confidencePercent}%
                        </div>
                    </div>
                </div>
                <div class="result-item">
                    <strong>Language:</strong> ${data.language}
                </div>
                <div class="result-item">
                    <strong>Explanation:</strong> ${data.explanation}
                </div>
                ${data.audioQuality ? `
                <div class="result-item">
                    <strong>Audio Quality:</strong> ${(data.audioQuality.qualityScore * 100).toFixed(1)}%
                    <br><small>Sample Rate: ${data.audioQuality.sampleRate}Hz | Duration: ${data.audioQuality.duration.toFixed(2)}s</small>
                </div>
                ` : ''}
            `;
        }
        
        function showError(message) {
            result.className = 'result error show';
            document.getElementById('resultTitle').textContent = 'Error';
            document.getElementById('resultContent').innerHTML = `<p>${message}</p>`;
        }
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)
