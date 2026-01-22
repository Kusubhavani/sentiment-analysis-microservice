import os
import logging
import numpy as np
from typing import Tuple
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing.sequence import pad_sequences
import pickle

logger = logging.getLogger(__name__)

class ModelService:
    def __init__(self):
        self.model_path = os.getenv("MODEL_PATH", "/app/models/sentiment_model.h5")
        self.tokenizer_path = "/app/models/tokenizer.pkl"
        self.model = None
        self.tokenizer = None
        self.max_length = 128
        self.vocab_size = 10000
        self.load_model()
    
    def load_model(self):
        """Load or create sentiment analysis model"""
        try:
            # Try to load pre-trained model
            if os.path.exists(self.model_path):
                self.model = load_model(self.model_path)
                logger.info(f"Loaded model from {self.model_path}")
                
                # Load or create tokenizer
                if os.path.exists(self.tokenizer_path):
                    with open(self.tokenizer_path, 'rb') as f:
                        self.tokenizer = pickle.load(f)
                    logger.info(f"Loaded tokenizer from {self.tokenizer_path}")
                else:
                    self._create_dummy_tokenizer()
            else:
                # Create dummy model for development
                self._create_dummy_model()
                self._create_dummy_tokenizer()
                
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            # Fallback to mock model
            self._create_dummy_model()
            self._create_dummy_tokenizer()
    
    def _create_dummy_model(self):
        """Create a dummy model for development/testing"""
        from tensorflow.keras.models import Sequential
        from tensorflow.keras.layers import Embedding, LSTM, Dense
        
        logger.info("Creating dummy sentiment model...")
        
        model = Sequential([
            Embedding(self.vocab_size, 16, input_length=self.max_length),
            LSTM(32),
            Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer='adam',
            loss='binary_crossentropy',
            metrics=['accuracy']
        )
        
        # Train on minimal dummy data
        dummy_data = np.random.randint(0, 1000, (10, self.max_length))
        dummy_labels = np.random.randint(0, 2, (10, 1))
        model.fit(dummy_data, dummy_labels, epochs=1, verbose=0)
        
        # Save model
        os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
        model.save(self.model_path)
        self.model = model
        
        logger.info(f"Dummy model created and saved to {self.model_path}")
    
    def _create_dummy_tokenizer(self):
        """Create a dummy tokenizer for development"""
        from tensorflow.keras.preprocessing.text import Tokenizer
        
        logger.info("Creating dummy tokenizer...")
        
        self.tokenizer = Tokenizer(num_words=self.vocab_size)
        
        # Fit on some dummy text
        dummy_texts = [
            "This is a positive review",
            "This is a negative review",
            "I love this product",
            "I hate this product",
            "Great service and amazing quality",
            "Terrible experience and poor support"
        ]
        self.tokenizer.fit_on_texts(dummy_texts)
        
        # Save tokenizer
        with open(self.tokenizer_path, 'wb') as f:
            pickle.dump(self.tokenizer, f)
        
        logger.info(f"Tokenizer created and saved to {self.tokenizer_path}")
    
    def preprocess_text(self, text: str):
        """Preprocess text for model input"""
        try:
            # Tokenize and pad
            sequence = self.tokenizer.texts_to_sequences([text])
            padded = pad_sequences(sequence, maxlen=self.max_length)
            return padded
        except Exception as e:
            logger.error(f"Error preprocessing text: {str(e)}")
            # Return dummy data on error
            return np.zeros((1, self.max_length))
    
    def predict(self, text: str) -> Tuple[str, float]:
        """Predict sentiment for given text"""
        try:
            # Use real model if available
            if self.model:
                processed_text = self.preprocess_text(text)
                prediction = self.model.predict(processed_text, verbose=0)
                score = float(prediction[0][0])
            else:
                # Fallback to mock prediction
                score = self._mock_prediction(text)
            
            sentiment = "positive" if score >= 0.5 else "negative"
            
            logger.debug(f"Prediction: {sentiment} ({score:.4f}) for text: {text[:50]}...")
            return sentiment, score
            
        except Exception as e:
            logger.error(f"Error making prediction: {str(e)}")
            # Return neutral as fallback
            return "neutral", 0.5
    
    def _mock_prediction(self, text: str) -> float:
        """Mock sentiment prediction (fallback)"""
        # Simple keyword-based sentiment
        positive_words = ['good', 'great', 'excellent', 'love', 'amazing', 'awesome', 'best']
        negative_words = ['bad', 'terrible', 'awful', 'hate', 'worst', 'poor']
        
        text_lower = text.lower()
        
        pos_count = sum(1 for word in positive_words if word in text_lower)
        neg_count = sum(1 for word in negative_words if word in text_lower)
        
        total = pos_count + neg_count
        if total > 0:
            return pos_count / total
        return 0.5
    
    def is_loaded(self):
        """Check if model is loaded"""
        return self.model is not None
