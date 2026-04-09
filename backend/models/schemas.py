from pydantic import BaseModel, EmailStr
from typing import Dict, Optional, List
from datetime import datetime

class BlogRequest(BaseModel):
    workspace_name: str # <--- NEW: Requires a name before generation starts
    keyword: str
    domain: str = "General"
    scheduled_for: Optional[datetime] = None

class BlogResponse(BaseModel):
    workspace_name: str
    keyword: str
    domain: str
    outline: str
    blog_content: str
    summary: str # <--- NEW: Returning the RAG-Lite summary
    seo_score: int
    keyword_density: Optional[float] = 0.0 
    twitter_thread: Optional[str] = None
    linkedin_post: Optional[str] = None
    naturalness: int
    snippet_readiness: str
    readability_level: str

class PublishRequest(BaseModel):
    title: str
    content: str

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    gemini_key: Optional[str] = None
    devto_key: Optional[str] = None
    hashnode_token: Optional[str] = None
    hashnode_pub_id: Optional[str] = None
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

class UserUpdateSettings(BaseModel):
    gemini_key: Optional[str] = None
    devto_key: Optional[str] = None
    hashnode_token: Optional[str] = None
    hashnode_pub_id: Optional[str] = None
    brand_voice: Optional[str] = None

# --- MEGA UPDATE: WORKSPACE SCHEMAS ---

class WorkspaceResponse(BaseModel):
    id: int
    workspace_name: str
    keyword: Optional[str] = None
    domain: Optional[str] = None
    status: str
    summary: Optional[str] = None
    
    # --- THE AMNESIA FIX ---
    content: Optional[str] = None 
    seo_score: Optional[float] = None
    naturalness: Optional[int] = None 
    readability_level: Optional[str] = None 
    twitter_thread: Optional[str] = None 
    linkedin_post: Optional[str] = None 
    
    scheduled_for: Optional[datetime] = None
    devto_url: Optional[str] = None
    hashnode_url: Optional[str] = None
    created_at: datetime
    last_edited: datetime 
    
    class Config:
        from_attributes = True

class WorkspaceSaveRequest(BaseModel):
    """Used for the background auto-save loop in the Studio"""
    content: str

class CorrectionRequest(BaseModel):
    """Used for the Human-in-the-Loop AI Editor"""
    instruction: str
    current_content: str

# --- IDEA BOT & NOTES SCHEMAS ---

class NoteRequest(BaseModel):
    title: str
    content: str
    is_bulleted: bool

class MuseRequest(BaseModel):
    message: str

class MuseResponse(BaseModel):
    reply: str

class AutocompleteRequest(BaseModel):
    prefix: str

class CorrectionRequest(BaseModel):
    instruction: str
    current_content: str