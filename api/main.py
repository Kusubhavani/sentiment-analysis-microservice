import logging
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Scalable AI Sentiment Analysis Microservice",
    description="Production-ready sentiment analysis with async processing and MongoDB",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router, prefix="/api")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.info("Health check requested")
    return {
        "status": "healthy",
        "service": "sentiment-analysis-api",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "message": "Sentiment Analysis Microservice",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "sync_analysis": "POST /api/sentiment/sync",
            "async_analysis": "POST /api/sentiment/async",
            "get_result": "GET /api/sentiment/results/{job_id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
