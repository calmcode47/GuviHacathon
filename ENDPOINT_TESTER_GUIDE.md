# Endpoint Tester Guide

## Steps
1. Enter API URL: https://your-railway-url.railway.app/api/voice-detection
2. Enter API Key/Authorization: sk_live_guvihackathon_2026
3. Add test message: "Round 2 English voice detection API"
4. Enter audio URL: https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3
5. Click "Test Endpoint"
6. Expected success response:
   {
     "status": "success",
     "language": "English",
     "classification": "AI_GENERATED | HUMAN | BORDERLINE",
     "confidenceScore": 0.87,
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

## Troubleshooting
- 401 Unauthorized: Check that the API key matches the Railway environment variable
- 400 Bad Request: Verify the URL is accessible and points to an MP3 file
- 408 Timeout: The URL may be slow or unreachable; try another sample
- 500 Server Error: Check Railway logs for details
