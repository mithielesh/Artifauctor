# backend/models/db_models.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    
    # --- BYOK: Bring Your Own Key Storage ---
    gemini_key = Column(String, nullable=True)
    devto_key = Column(String, nullable=True)
    hashnode_token = Column(String, nullable=True)
    hashnode_pub_id = Column(String, nullable=True)
    
    # --- Feature: Brand Voice ---
    brand_voice = Column(Text, nullable=True) 
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationship to link users to their generated articles
    articles = relationship("ArticleHistory", back_populates="owner")


class ArticleHistory(Base):
    __tablename__ = "article_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    keyword = Column(String)
    domain = Column(String)
    content = Column(Text)
    seo_score = Column(Float)
    status = Column(String) # "Draft", "Published", or "Scheduled"
    
    # --- INDEPENDENT URL TRACKING ---
    devto_url = Column(String, nullable=True)
    hashnode_url = Column(String, nullable=True)
    
    # --- NEW COLUMNS FOR STAGE 2 (Socials & Scheduling) ---
    scheduled_for = Column(DateTime, nullable=True)
    target_platform = Column(String, nullable=True) 
    twitter_thread = Column(Text, nullable=True)
    linkedin_post = Column(Text, nullable=True)
    
    # FIX: Changed server_default to default with a lambda
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationship back to the user
    owner = relationship("User", back_populates="articles")