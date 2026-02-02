from typing import Literal, Optional
from pydantic import BaseModel, Field

LanguageLiteral = Literal["Tamil", "English", "Hindi", "Malayalam", "Telugu"]

class VoiceDetectionRequest(BaseModel):
    language: LanguageLiteral = Field(..., description="One of the supported languages")
    audioFormat: Literal["mp3"] = Field(..., description="Must be 'mp3'")
    audioBase64: str = Field(..., description="Base64-encoded MP3 audio")

class VoiceDetectionResponse(BaseModel):
    status: Literal["success"]
    language: LanguageLiteral
    classification: Literal["AI_GENERATED", "HUMAN"]
    confidenceScore: float
    explanation: str

class ErrorResponse(BaseModel):
    status: Literal["error"]
    message: str