import os
from typing import Set

SUPPORTED_LANGUAGES: Set[str] = {"Tamil", "English", "Hindi", "Malayalam", "Telugu"}
EXPECTED_AUDIO_FORMAT = "mp3"

# Default key only for local testing; override via environment variable in deployment.
API_KEY = os.getenv("API_KEY", "sk_test_123456789")

# Input guardrails (configurable via env)
# Max Base64-decoded audio bytes; default 10 MB
MAX_AUDIO_BYTES = int(os.getenv("MAX_AUDIO_BYTES", str(10 * 1024 * 1024)))
# Max audio duration in seconds; default 60s
MAX_DURATION_SECONDS = float(os.getenv("MAX_DURATION_SECONDS", "60"))