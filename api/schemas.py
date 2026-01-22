from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class SentimentRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        example="I love this product! It's amazing.",
        description="Text to analyze for sentiment"
    )

class SyncSentimentResponse(BaseModel):
    text: str = Field(..., description="Original text")
    sentiment: str = Field(..., description="positive or negative")
    score: float = Field(..., ge=0.0, le=1.0, description="Sentiment confidence score")
    processing_time: float = Field(..., description="Processing time in seconds")

class AsyncSentimentResponse(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="processing")
    message: str = Field(..., description="Status message")
    timestamp: datetime = Field(..., description="Job submission timestamp")

class SentimentResult(BaseModel):
    job_id: str = Field(..., description="Unique job identifier")
    text: str = Field(..., description="Original text")
    sentiment: str = Field(..., description="positive or negative")
    score: float = Field(..., ge=0.0, le=1.0, description="Sentiment confidence score")
    timestamp: datetime = Field(..., description="Job submission timestamp")
    processed_at: datetime = Field(..., description="Processing completion timestamp")
    processing_time: float = Field(..., description="Total processing time in seconds")

class HealthResponse(BaseModel):
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="Service version")

class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error description")
    error_code: Optional[str] = Field(None, description="Error code")
    timestamp: datetime = Field(..., description="Error timestamp")
