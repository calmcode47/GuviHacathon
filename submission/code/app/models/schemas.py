from typing import Literal, Optional, List
from pydantic import BaseModel, Field


class VoiceDetectionRequest(BaseModel):
    audioFormat: Literal["mp3"] = Field(..., description="Must be 'mp3'")
    audioBase64: str = Field(..., description="Base64-encoded MP3 audio")


class BatchVoiceDetectionRequest(BaseModel):
    samples: List[VoiceDetectionRequest] = Field(..., description="List of audio samples to process")


class AudioQualityMetrics(BaseModel):
    sampleRate: int
    duration: float
    channels: int
    isValidFormat: bool
    qualityScore: float = Field(..., description="Quality score from 0.0 to 1.0")


class VoiceDetectionResponse(BaseModel):
    status: Literal["success"]
    classification: Literal["AI_GENERATED", "HUMAN"]
    confidenceScore: float
    confidenceCategory: Literal["low", "medium", "high"] = Field(default="medium", description="Confidence category")
    explanation: str
    audioQuality: Optional[AudioQualityMetrics] = None


class BatchVoiceDetectionResponse(BaseModel):
    status: Literal["success"]
    results: List[VoiceDetectionResponse]
    totalProcessed: int
    totalFailed: int


class ErrorResponse(BaseModel):
    status: Literal["error"]
    message: str
