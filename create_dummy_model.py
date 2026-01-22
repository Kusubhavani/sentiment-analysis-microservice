#!/usr/bin/env python3
"""
Create dummy sentiment analysis model for development/testing.
Run this script before starting the services if you don't have a pre-trained model.
"""

import os
import sys
import numpy as np
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Embedding, LSTM, Dense
from tensorflow.keras.preprocessing.text import Tokenizer
import pickle

def create_dummy_model():
    """Create and save a dummy sentiment analysis model"""
    
    print("Creating dummy sentiment analysis model...")
    
    # Create models directory if it doesn't exist
    models_dir = "./models"
    os.makedirs(models_dir, exist_ok=True)
    
    # Model parameters
    vocab_size = 10000
    embedding_dim = 16
    max_length = 128
    
    # Create model architecture
    model = Sequential([
        Embedding(vocab_size, embedding_dim, input_length=max_length),
        LSTM(32),
        Dense(1, activation='sigmoid')
    ])
    
    # Compile model
    model.compile(
        optimizer='adam',
        loss='binary_crossentropy',
        metrics=['accuracy']
    )
    
    # Create dummy training data
    print("Generating dummy training data...")
    
    # Sample texts for training
    positive_texts = [
        "I love this amazing product",
        "Excellent service and great support",
        "Highly recommended for everyone",
        "Best purchase I've ever made",
        "Outstanding quality and value",
        "Absolutely fantastic experience",
        "Couldn't be happier with this",
        "Top notch performance and reliability",
        "Exceeded all my expectations",
        "Perfect for my needs"
    ]
    
    negative_texts = [
        "Terrible product, do not buy",
        "Worst experience of my life",
        "Poor quality and broke quickly",
        "Complete waste of money",
        "Horrible customer service",
        "Extremely disappointed with this",
        "Failed after just one use",
        "Not worth the price at all",
        "Awful performance and unreliable",
        "Regret buying this product"
    ]
    
    all_texts = positive_texts + negative_texts
    labels = [1] * len(positive_texts) + [0] * len(negative_texts)
    
    # Create and fit tokenizer
    print("Creating tokenizer...")
    tokenizer = Tokenizer(num_words=vocab_size)
    tokenizer.fit_on_texts(all_texts)
    
    # Convert texts to sequences
    sequences = tokenizer.texts_to_sequences(all_texts)
    padded_sequences = tf.keras.preprocessing.sequence.pad_sequences(
        sequences, maxlen=max_length, padding='post'
    )
    
    # Train model on dummy data
    print("Training dummy model (one epoch)...")
    model.fit(
        padded_sequences,
        np.array(labels),
        epochs=1,
        batch_size=2,
        verbose=1
    )
    
    # Save model
    model_path = os.path.join(models_dir, "sentiment_model.h5")
    model.save(model_path)
    print(f"✅ Model saved to: {model_path}")
    
    # Save tokenizer
    tokenizer_path = os.path.join(models_dir, "tokenizer.pkl")
    with open(tokenizer_path, 'wb') as f:
        pickle.dump(tokenizer, f)
    print(f"✅ Tokenizer saved to: {tokenizer_path}")
    
    # Test the model
    print("\nTesting the model...")
    test_texts = [
        "This is absolutely wonderful",
        "I hate this terrible thing",
        "It's okay, nothing special"
    ]
    
    for text in test_texts:
        sequence = tokenizer.texts_to_sequences([text])
        padded = tf.keras.preprocessing.sequence.pad_sequences(
            sequence, maxlen=max_length, padding='post'
        )
        prediction = model.predict(padded, verbose=0)[0][0]
        sentiment = "positive" if prediction >= 0.5 else "negative"
        print(f"  '{text[:30]}...' -> {sentiment} ({prediction:.4f})")
    
    print("\n✅ Dummy model creation complete!")
    print(f"Model file: {model_path}")
    print(f"Tokenizer: {tokenizer_path}")
    print("\nYou can now start the services with: docker-compose up --build")

if __name__ == "__main__":
    try:
        create_dummy_model()
    except Exception as e:
        print(f"❌ Error creating dummy model: {e}")
        sys.exit(1)
