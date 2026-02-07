# Debugging Guide

**Invalid URL format**
- Ensure the URL starts with http:// or https:// and includes a domain.
- Try opening the URL in a browser to verify.

**Download timeout**
- Verify the URL is publicly accessible and fast enough.
- Check network connectivity; retry later.
- Large files may approach timeout; use smaller samples.

**File is not MP3 format**
- Check Content-Type header indicates audio/mpeg or similar.
- Confirm the file has MP3 magic headers (ID3 or MPEG frame sync).
- Use a different source URL that serves MP3 files.

**Both auth methods fail**
- Confirm API_KEY environment variable matches the provided token.
- For Bearer, ensure header value is “Bearer <token>”.
- For x-api-key, ensure header name is exactly x-api-key.

**Unsupported audio format**
- audioFormat must be "mp3".
- Check the request payload fields are correctly named.

**Provide either audioBase64 or audioUrl**
- Exactly one of audioBase64 or audioUrl must be set.
- Remove one field if both are present; add one if neither.

**Server not responding**
- Verify the server is running on localhost:8000.
- Check Docker container logs or uvicorn logs for errors.
