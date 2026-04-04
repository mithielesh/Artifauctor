from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, Date, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone, date
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

    # Relationship to link users to their workspaces
    workspaces = relationship("Workspace", back_populates="owner")


class Workspace(Base):
    __tablename__ = "workspaces"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    # --- MEGA UPDATE: Workspace Identity ---
    workspace_name = Column(String, nullable=False)
    status = Column(String, default="Drafting") # "Drafting", "Generating", "Scheduled", "Published"
    summary = Column(Text, nullable=True) # <-- New RAG-Lite Context Engine
    
    keyword = Column(String)
    domain = Column(String)
    content = Column(Text)
    
    # --- ML METRICS (Amnesia Fix) ---
    seo_score = Column(Float)
    naturalness = Column(Integer, nullable=True)
    readability_level = Column(String, nullable=True)
    
    # --- INDEPENDENT URL TRACKING ---
    devto_url = Column(String, nullable=True)
    hashnode_url = Column(String, nullable=True)
    
    # --- SOCIALS & SCHEDULING ---
    scheduled_for = Column(DateTime, nullable=True)
    target_platform = Column(String, nullable=True) 
    twitter_thread = Column(Text, nullable=True)
    linkedin_post = Column(Text, nullable=True)
    
    # --- TIME TRACKING ---
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    # onupdate automatically refreshes this timestamp whenever the row is modified!
    last_edited = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationship back to the user
    owner = relationship("User", back_populates="workspaces")

    # Ensure workspace names are unique PER USER, but allow different users to use the same name
    __table_args__ = (
        UniqueConstraint('user_id', 'workspace_name', name='_user_workspace_uc'),
    )


class AnalyticsHistory(Base):
    """Stores daily snapshots of Dev.to and Hashnode performance."""
    __tablename__ = "analytics_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    
    recorded_date = Column(Date, default=date.today) 
    total_views = Column(Integer, default=0)
    total_likes = Column(Integer, default=0)
    total_comments = Column(Integer, default=0)


class IdeaNote(Base):
    __tablename__ = "idea_notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String, default="Untitled") 
    content = Column(String)
    is_bulleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)