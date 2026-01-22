import logging
import uuid
import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from api.schemas import (
    SentimentRequest,
    SyncSentimentResponse,
    AsyncSentimentResponse,
    SentimentResult,
    ErrorResponse
)
from api.services.queue_service import QueueService
from api.services.database_service import DatabaseService

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sentiment"])

# In-memory cache for sync requests (simple implementation)
sync_model = None

def load_sync_model():
    """Lazy load model for sync requests"""
    global sync_model
    if sync_model is None:
        try:
            from api.services.model_service import ModelService
            sync_model = ModelService()
            logger.info("Sync model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load sync model: {str(e)}")
            raise
    return sync_model

@router.post(
    "/sentiment/sync",
    response_model=SyncSentimentResponse,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def analyze_sentiment_sync(request: SentimentRequest):
    """Synchronous sentiment analysis endpoint
    
    Process sentiment analysis immediately and return result.
    Useful for real-time analysis with small text.
    """
    logger.info(f"Sync sentiment analysis request: {len(request.text)} chars")
    
    try:
        model_service = load_sync_model()
        
        start_time = time.time()
        sentiment, score = model_service.predict(request.text)
        processing_time = time.time() - start_time
        
        logger.info(f"Sync analysis completed: {sentiment} ({score:.4f}) in {processing_time:.3f}s")
        
        return SyncSentimentResponse(
            text=request.text[:100] + ("..." if len(request.text) > 100 else ""),
            sentiment=sentiment,
            score=score,
            processing_time=processing_time
        )
    except ValueError as e:
        logger.warning(f"Validation error in sync analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in sync sentiment analysis: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during sentiment analysis"
        )

@router.post(
    "/sentiment/async",
    response_model=AsyncSentimentResponse,
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def analyze_sentiment_async(request: SentimentRequest):
    """Asynchronous sentiment analysis endpoint
    
    Submit text for background processing. Returns job ID to retrieve results later.
    Ideal for batch processing or long texts.
    """
    logger.info(f"Async sentiment analysis request: {len(request.text)} chars")
    
    try:
        # Generate unique job ID
        job_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        # Create message payload
        message = {
            "job_id": job_id,
            "text": request.text,
            "timestamp": timestamp,
            "status": "submitted"
        }
        
        # Send to queue
        queue_service = QueueService()
        queue_service.publish_message(message)
        
        logger.info(f"Job submitted to queue: {job_id}")
        
        return AsyncSentimentResponse(
            job_id=job_id,
            status="processing",
            message="Sentiment analysis job submitted successfully. Use job_id to retrieve results.",
            timestamp=datetime.now()
        )
    except Exception as e:
        logger.error(f"Error submitting async job: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit job to processing queue"
        )

@router.get(
    "/sentiment/results/{job_id}",
    response_model=SentimentResult,
    responses={
        404: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def get_sentiment_result(job_id: str):
    """Get sentiment analysis result by job ID
    
    Retrieve the result of an async sentiment analysis job.
    Returns 404 if job not found or still processing.
    """
    logger.info(f"Result request for job: {job_id}")
    
    try:
        db_service = DatabaseService()
        result = db_service.get_result(job_id)
        
        if not result:
            logger.warning(f"Job not found: {job_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Job ID '{job_id}' not found or still processing"
            )
        
        # Calculate processing time
        timestamp = datetime.fromisoformat(result["timestamp"].replace("Z", ""))
        processed_at = datetime.fromisoformat(result["processed_at"].replace("Z", ""))
        processing_time = (processed_at - timestamp).total_seconds()
        
        result["processing_time"] = processing_time
        
        logger.info(f"Result retrieved for job: {job_id}")
        return SentimentResult(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving result for job {job_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving sentiment analysis result"
        )
