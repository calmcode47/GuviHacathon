# Design Approach - URL Support & Dual Auth

## URL Input Support
- Added a downloader utility that:
  - Validates URL format
  - Enforces max file size (50MB)
  - Checks MP3 signature (ID3 or frame sync)
  - Streams content to limit memory usage
  - Returns Base64 for compatibility with existing pipeline

## Dual Authentication
- Endpoint extracts API key from either:
  - x-api-key header
  - Authorization: Bearer header
- Compares against API_KEY environment variable

## Error Handling
- Structured JSON with status/message/code across 400/401/408/413/500
- Oversized audio mapped to HTTP 413

## Compatibility
- Base64 path unchanged
- Feature extraction and classifier remain identical

## Performance
- URL fetch timeout: 30s
- Response time generally under 2s in local tests (depends on audio length and network)
