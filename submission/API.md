API Reference (English-Only)

- Endpoint: POST /api/voice-detection
- Description: Detects AI-generated vs Human voices in English audio
- Request (JSON):
  {
    "audioFormat": "mp3",
    "audioBase64": "<base64-encoded mp3>"
  }
- Response (JSON):
  {
    "status": "success",
    "classification": "AI_GENERATED",
    "confidenceScore": 0.92,
    "explanation": "Unnatural pitch stability detected",
    "audioQuality": {
      "sampleRate": 16000,
      "duration": 14.9,
      "channels": 1,
      "isValidFormat": true,
      "qualityScore": 0.85
    }
  }
- cURL Example:
  curl -X POST http://localhost:8000/api/voice-detection \
    -H "Content-Type: application/json" \
    -H "x-api-key: sk_test_123456789" \
    -d '{"audioFormat":"mp3","audioBase64":"<base64>"}'
- Errors:
  - 400: Invalid audio format or malformed request
  - 401: Invalid API key
  - 500: Processing error
- Notes:
  - Currently optimized for English language audio
  - Rate limits may apply
