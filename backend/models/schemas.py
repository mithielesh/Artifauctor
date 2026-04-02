from pydantic import BaseModel, EmailStr
from typing import Dict, Optional, List
from datetime import datetime

class BlogRequest(BaseModel):
    keyword: str
    domain: str = "General"
    auto_publish: bool = False  # The frontend will toggle this to True when you click "Deploy"

class BlogResponse(BaseModel):
    keyword: str
    domain: str
    outline: str
    blog_content: str
    seo_score: int
    keyword_density: float
    twitter_thread: Optional[str] = None
    linkedin_post: Optional[str] = None
    naturalness: int
    snippet_readiness: str
    readability_level: str
    published_urls: Optional[Dict[str, str]] = {} # Will hold our Medium and Dev.to links

# Add this to models/schemas.py
class PublishRequest(BaseModel):
    title: str
    content: str

# Data expected from the user when creating an account
class UserCreate(BaseModel):
    email: EmailStr
    password: str

# Data we send back to the user (never send the password back!)
class UserResponse(BaseModel):
    id: int
    email: str
    gemini_key: Optional[str] = None
    devto_key: Optional[str] = None
    hashnode_token: Optional[str] = None
    hashnode_pub_id: Optional[str] = None
    
    class Config:
        from_attributes = True

# The JWT Token payload
class Token(BaseModel):
    access_token: str
    token_type: str

# Data expected when a user updates their settings (BYOK & Brand Voice)
class UserUpdateSettings(BaseModel):
    gemini_key: Optional[str] = None
    devto_key: Optional[str] = None
    hashnode_token: Optional[str] = None
    hashnode_pub_id: Optional[str] = None
    brand_voice: Optional[str] = None

# Data sent back when fetching the Vault history
class ArticleHistoryResponse(BaseModel):
    id: int
    keyword: str
    domain: str
    status: str
    seo_score: Optional[float] = None
    devto_url: Optional[str] = None
    hashnode_url: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True