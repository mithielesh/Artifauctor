from pydantic import BaseModel
from typing import Dict, Optional

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
    naturalness: int
    snippet_readiness: str
    readability_level: str
    published_urls: Optional[Dict[str, str]] = {} # Will hold our Medium and Dev.to links

# Add this to models/schemas.py
class PublishRequest(BaseModel):
    title: str
    content: str