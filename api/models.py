# This file can be used for SQLAlchemy models if needed
# Currently using MongoDB directly, so keeping it empty

# Example if you want to add database models later:
# from sqlalchemy import Column, Integer, String, Float, DateTime
# from sqlalchemy.ext.declarative import declarative_base

# Base = declarative_base()

# class SentimentResult(Base):
#     __tablename__ = "sentiment_results"
    
#     id = Column(Integer, primary_key=True, index=True)
#     job_id = Column(String, unique=True, index=True)
#     text = Column(String)
#     sentiment = Column(String)
#     score = Column(Float)
#     timestamp = Column(DateTime)
#     processed_at = Column(DateTime)
