import logging
import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, DuplicateKeyError, OperationFailure

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017/sentiment_db")
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                self.client = MongoClient(
                    self.mongodb_url,
                    serverSelectionTimeoutMS=5000,
                    maxPoolSize=50,
                    retryWrites=True
                )
                # Test connection
                self.client.admin.command('ping')
                self.db = self.client.sentiment_db
                self.collection = self.db.sentiment_results
                
                logger.info(f"Worker connected to MongoDB (attempt {attempt + 1})")
                return
                
            except ConnectionFailure as e:
                logger.warning(f"Failed to connect to MongoDB (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                else:
                    logger.error("Max retries reached for MongoDB connection")
                    raise
    
    def get_result(self, job_id: str):
        """Get existing result by job ID"""
        try:
            return self.collection.find_one({"job_id": job_id})
        except Exception as e:
            logger.error(f"Error checking for existing result: {str(e)}")
            return None
    
    def save_result(self, result: dict):
        """Save sentiment analysis result to MongoDB"""
        try:
            self.collection.insert_one(result)
            logger.debug(f"Result saved for job: {result['job_id']}")
        except DuplicateKeyError:
            logger.warning(f"Duplicate job_id detected: {result['job_id']}")
            # Update existing record
            self.collection.update_one(
                {"job_id": result["job_id"]},
                {"$set": result}
            )
        except Exception as e:
            logger.error(f"Error saving result to MongoDB: {str(e)}")
            raise
    
    def check_connection(self):
        """Check if MongoDB is reachable"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB connection check failed: {str(e)}")
            return False
