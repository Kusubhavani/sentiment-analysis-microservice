import os
import logging
import numpy as np
from typing import Tuple

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self):
        """Initialize a mock model service for development"""
        logger.info("Initializing ModelService (mock implementation)")
        self.model_loaded = True
    
    def predict(self, text: str) -> Tuple[str, float]:
        """Mock sentiment prediction for development
        
        In production, this would load a real TensorFlow/Keras model.
        """
        # Simple mock sentiment analysis based on keywords
        positive_keywords = ['love', 'great', 'excellent', 'good', 'amazing', 'awesome', 'best']
        negative_keywords = ['hate', 'terrible', 'bad', 'awful', 'worst', 'poor']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        total = positive_count + negative_count
        if total > 0:
            score = positive_count / total
        else:
            # Neutral if no keywords found
            score = 0.5
        
        # Add some randomness to make it interesting
        import random
        score = max(0.0, min(1.0, score + random.uniform(-0.2, 0.2)))
        
        sentiment = "positive" if score >= 0.5 else "negative"
        
        logger.debug(f"Mock prediction: {sentiment} ({score:.4f}) for text: {text[:50]}...")
        
        return sentiment, float(score)
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self.model_loaded
