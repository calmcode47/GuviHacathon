from typing import Literal, Optional, List
from pydantic import BaseModel, Field

LanguageLiteral = Literal["Tamil", "English", "Hindi", "Malayalam", "Telugu"]

class VoiceDetectionRequest(BaseModel):
    language: LanguageLiteral = Field(..., description="One of the supported languages")
    audioFormat: Literal["mp3"] = Field(..., description="Must be 'mp3'")
    audioBase64: Optional[str] = Field(None, description="Base64-encoded MP3 audio")
    audioUrl: Optional[str] = Field(None, description="Public URL to an MP3 file")

class AudioQuality(BaseModel):
    formatValid: bool
    sampleRateSuspect: bool
    shortAudio: bool
    durationSeconds: float
    sampleRate: int
    channels: int

class VoiceDetectionResponse(BaseModel):
    status: Literal["success"]
    language: LanguageLiteral
    classification: Literal["AI_GENERATED", "HUMAN", "BORDERLINE"]
    confidenceScore: float
    explanation: str
    audioQuality: AudioQuality

class BatchAudioRequest(BaseModel):
    language: LanguageLiteral = Field(..., description="One of the supported languages")
    audioFormat: Literal["mp3"] = Field(..., description="Must be 'mp3'")
    audioBase64: str = Field(..., description="Base64-encoded MP3 audio")

class BatchDetectionRequest(BaseModel):
    audio_samples: List[BatchAudioRequest] = Field(..., description="List of audio samples to analyze")

class BatchResult(BaseModel):
    index: int
    status: Literal["success", "error"]
    language: Optional[LanguageLiteral] = None
    classification: Optional[Literal["AI_GENERATED", "HUMAN", "BORDERLINE"]] = None
    confidenceScore: Optional[float] = None
    explanation: Optional[str] = None
    message: Optional[str] = None

class BatchDetectionResponse(BaseModel):
    status: Literal["success"]
    total_samples: int
    results: List[BatchResult]

class ErrorResponse(BaseModel):
    status: Literal["error"]
    message: str
