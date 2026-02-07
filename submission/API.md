# Voice Detection API - Round 2

## Endpoints
- POST /api/voice-detection
- GET /health

## Request Formats
- Method 1 — Base64 Input
  - Headers: Content-Type: application/json; x-api-key: your_key
  - Body:
    {
      "language": "English",
      "audioFormat": "mp3",
      "audioBase64": "base64_encoded_audio"
    }

- Method 2 — URL Input
  - Headers: Content-Type: application/json; Authorization: Bearer your_key
  - Body:
    {
      "language": "English",
      "audioFormat": "mp3",
      "audioUrl": "https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"
    }

## Authentication
- Supported headers:
  - x-api-key: your_api_key
  - Authorization: Bearer your_api_key
- Either format is accepted.

## Error Responses
- 400: Invalid input (both/neither provided, invalid URL, unsupported format)
- 401: Authentication failed
- 408: URL download timeout (>30s)
- 413: File too large (>50MB)
- 500: Internal server error
- Format:
  {
    "status": "error",
    "message": "Detailed error message",
    "code": 400
  }

## Success Response
{
  "status": "success",
  "language": "English",
  "classification": "AI_GENERATED | HUMAN | BORDERLINE",
  "confidenceScore": 0.0-1.0,
  "explanation": "...",
  "audioQuality": {
    "formatValid": true,
    "sampleRateSuspect": false,
    "shortAudio": false,
    "durationSeconds": 12.34,
    "sampleRate": 22050,
    "channels": 1
  }
}

## cURL Examples
- Base64 (x-api-key):
  curl -X POST "https://your-railway-url.railway.app/api/voice-detection" \
    -H "Content-Type: application/json" \
    -H "x-api-key: sk_live_guvihackathon_2026" \
    -d '{"language":"English","audioFormat":"mp3","audioBase64":"SUQz..."}'

- URL (Bearer):
  curl -X POST "https://your-railway-url.railway.app/api/voice-detection" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer sk_live_guvihackathon_2026" \
    -d '{"language":"English","audioFormat":"mp3","audioUrl":"https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"}'
