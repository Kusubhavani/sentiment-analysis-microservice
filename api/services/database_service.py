import logging
import os
from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self):
        self.mongodb_url = os.getenv("MONGODB_URL", "mongodb://mongodb:27017/sentiment_db")
        self.client = None
        self.db = None
        self.collection = None
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection with error handling"""
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
            
            # Create indexes for better performance
            self.collection.create_index("job_id", unique=True)
            self.collection.create_index("timestamp")
            self.collection.create_index([("sentiment", 1), ("score", -1)])
            
            logger.info("Successfully connected to MongoDB")
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {str(e)}")
            raise Exception(f"MongoDB connection failed: {str(e)}")
        except ServerSelectionTimeoutError as e:
            logger.error(f"MongoDB server selection timeout: {str(e)}")
            raise Exception(f"MongoDB unavailable: {str(e)}")
    
    def get_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get sentiment analysis result by job ID"""
        try:
            result = self.collection.find_one({"job_id": job_id})
            if result:
                # Convert ObjectId to string
                result['_id'] = str(result['_id'])
                # Ensure proper datetime format
                for date_field in ['timestamp', 'processed_at']:
                    if date_field in result and not isinstance(result[date_field], str):
                        result[date_field] = result[date_field].isoformat()
                return result
            return None
        except OperationFailure as e:
            logger.error(f"MongoDB operation failed: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error retrieving result from MongoDB: {str(e)}")
            raise
    
    def check_connection(self):
        """Check if MongoDB is reachable"""
        try:
            self.client.admin.command('ping')
            return True
        except Exception as e:
            logger.error(f"MongoDB connection check failed: {str(e)}")
            return False
