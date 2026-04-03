# backend/api/routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import json
from datetime import timedelta
import datetime

# New Database & Auth Imports
from database import get_db
from models import schemas, db_models
from auth_utils import get_current_user

# Your existing services
from services.serp_scraper import fetch_top_serp_results
from services.agents import generate_seo_blog, generate_socials, call_the_muse
from services.validator import calculate_seo_score, calculate_humanness_score
from services.publisher import publish_to_devto, publish_to_hashnode

router = APIRouter()

# --- STAGE 1: THE AI PIPELINE ---

@router.post("/generate", response_model=schemas.BlogResponse)
async def generate_blog_endpoint(
    request: schemas.BlogRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    logging.info(f"PIPELINE START: {request.keyword} | Domain: {request.domain} | User: {current_user.email}")
    
    # 1. BYOK Check
    if not current_user.gemini_key:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API Key missing. Please configure it in The Vault (Settings)."
        )

    try:
        # --- RAG-LITE INTERNAL LINKING LOOKUP ---
        previous_articles = db.query(db_models.ArticleHistory).filter(
            db_models.ArticleHistory.user_id == current_user.id,
            db_models.ArticleHistory.status == "Published"
        ).order_by(db_models.ArticleHistory.id.desc()).limit(5).all()

        links_for_ai = []
        for art in previous_articles:
            # Use whichever URL is available
            url = art.devto_url or art.hashnode_url
            if url and url.strip():
                links_for_ai.append({"keyword": art.keyword, "url": url.strip()})
                
        print(f"DEBUG: Found {len(links_for_ai)} links for AI context: {links_for_ai}")

        # 2. THE EYES: Competitive SERP Research
        serp_data = fetch_top_serp_results(request.keyword, max_results=4)
        if not serp_data:
            raise HTTPException(status_code=500, detail="SERP Scraping Failed.")
            
        # 3. THE BRAIN: Enhanced Generation
        ai_result = generate_seo_blog(
            keyword=request.keyword, 
            serp_data=serp_data, 
            domain=request.domain,
            api_key=current_user.gemini_key,
            brand_voice=current_user.brand_voice,
            previous_links=links_for_ai
        )
        if not ai_result:
            raise HTTPException(status_code=500, detail="AI Generation Failed.")

        # --- AGENT 4 - SOCIAL MEDIA SPINOFFS ---
        socials = generate_socials(ai_result["blog_content"], current_user.gemini_key)
            
        # -----------------------------------------------------
        # 4. THE JUDGE: ML HYBRID VALIDATOR
        # -----------------------------------------------------
        logging.info("Running ML Validator & Perplexity Check...")
        seo_score = calculate_seo_score(ai_result["blog_content"], request.keyword, request.domain)
        humanness_data = calculate_humanness_score(ai_result["blog_content"])
        
        naturalness_score = humanness_data["naturalness"]
        readability_level = humanness_data["readability"]
        
        # Simple heuristic for snippets
        snippet_readiness = "High" if "<h2>" in ai_result["blog_content"] and "<ul>" in ai_result["blog_content"] else "Low"
        
        logging.info(f"PIPELINE COMPLETE: SEO Score {seo_score}/100 | Humanness: {naturalness_score}%")

        # 5. THE VAULT: Save with Socials & Scheduler
        new_article = db_models.ArticleHistory(
            user_id=current_user.id,
            keyword=request.keyword,
            domain=request.domain,
            content=ai_result["blog_content"],
            seo_score=float(seo_score),
            status="Draft",
            twitter_thread=socials.get("twitter"),
            linkedin_post=socials.get("linkedin"),
            scheduled_for=request.scheduled_for  # <-- THE SCHEDULER ACTIVATION
        )
        db.add(new_article)
        db.commit()
        db.refresh(new_article)

        # 6. Return Data exactly as the UI expects it
        return schemas.BlogResponse(
            keyword=request.keyword,
            domain=request.domain,
            outline=ai_result["outline"],
            blog_content=ai_result["blog_content"],
            seo_score=seo_score,                     # From ML Model
            naturalness=naturalness_score,           # From Textstat Variance
            readability_level=readability_level,     # From Flesch Check
            snippet_readiness=snippet_readiness,     # From Heuristics
            twitter_thread=socials.get("twitter"), 
            linkedin_post=socials.get("linkedin"),
            # Ensure keyword_density is in your schema, or default it to 0 since we use naturalness now
            keyword_density=0  
        )
        
    except Exception as e:
        logging.error(f"API ROUTE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- STAGE 2: THE PUBLISHING AGENTS (HITL) ---

@router.post("/publish/devto")
async def publish_devto_route(
    req: schemas.PublishRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Triggered manually by the 'Approve' button for Dev.to"""
    logging.info(f"Publishing Agent: Deploying to Dev.to for {current_user.email}...")
    
    if not current_user.devto_key:
        raise HTTPException(status_code=400, detail="Dev.to API Key missing in Settings.")

    url = publish_to_devto(req.title, req.content, current_user.devto_key)
    if not url:
        raise HTTPException(status_code=500, detail="Dev.to deployment failed.")
        
    # Mark the latest draft as Published in the Vault
    article = db.query(db_models.ArticleHistory).filter(
            db_models.ArticleHistory.user_id == current_user.id
        ).order_by(db_models.ArticleHistory.id.desc()).first()
        
    if article:
        article.status = "Published"
        article.devto_url = url # <-- Save specifically to Dev.to
        article.scheduled_for = None
        db.commit()

    return {"url": url}

@router.post("/publish/hashnode")
async def publish_hashnode_route(
    req: schemas.PublishRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Triggered manually by the 'Approve' button for Hashnode"""
    logging.info(f"Publishing Agent: Deploying to Hashnode for {current_user.email}...")
    
    if not current_user.hashnode_token or not current_user.hashnode_pub_id:
        raise HTTPException(status_code=400, detail="Hashnode Token or Publication ID missing in Settings.")

    url = publish_to_hashnode(req.title, req.content, current_user.hashnode_token, current_user.hashnode_pub_id)
    if not url:
        raise HTTPException(status_code=500, detail="Hashnode deployment failed.")
        
    # Mark the latest draft as Published in the Vault
    article = db.query(db_models.ArticleHistory).filter(
        db_models.ArticleHistory.user_id == current_user.id
    ).order_by(db_models.ArticleHistory.id.desc()).first()
        
    if article:
        article.status = "Published"
        article.hashnode_url = url # <-- Save specifically to Hashnode
        article.scheduled_for = None
        db.commit()

    return {"url": url}

@router.post("/publish/vault/{article_id}/{platform}")
async def publish_from_vault(
    article_id: int,
    platform: str,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    """Deploys a saved draft directly from the Vault to the specified platform."""
    
    # 1. Securely fetch the specific article belonging to this user
    article = db.query(db_models.ArticleHistory).filter(
        db_models.ArticleHistory.id == article_id,
        db_models.ArticleHistory.user_id == current_user.id
    ).first()

    if not article:
        raise HTTPException(status_code=404, detail="Article not found in your Vault.")
    
    # Reconstruct the standard title format
    title = f"The Future of {article.keyword}: A {article.domain} Deep-Dive"

    try:
        # 2. Route to the correct publisher based on the button clicked
        if platform == "devto":
            if not current_user.devto_key:
                raise HTTPException(status_code=400, detail="Dev.to API Key missing in Settings.")
            url = publish_to_devto(title, article.content, current_user.devto_key)

        elif platform == "hashnode":
            if not current_user.hashnode_token or not current_user.hashnode_pub_id:
                raise HTTPException(status_code=400, detail="Hashnode Token or Pub ID missing in Settings.")
            url = publish_to_hashnode(title, article.content, current_user.hashnode_token, current_user.hashnode_pub_id)
            
        else:
            raise HTTPException(status_code=400, detail="Unknown platform selected.")

        if not url:
            raise HTTPException(status_code=500, detail=f"{platform.capitalize()} deployment failed.")

        # 3. Update the specific Vault URL and Status!
        article.status = "Published"
        
        if platform == "devto":
            article.devto_url = url
        elif platform == "hashnode":
            article.hashnode_url = url

        article.scheduled_for = None
            
        db.commit()

        return {"url": url}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/analytics", tags=["SaaS Features"])
async def get_user_analytics(
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    """Fetches live publishing and reaction metrics for the last 7 days."""
    
    # 1. Check if the user has EVER published an article
    has_published = db.query(db_models.ArticleHistory).filter(
        db_models.ArticleHistory.user_id == current_user.id,
        db_models.ArticleHistory.status == 'Published'
    ).first() is not None

    # If they haven't published, we stop here and tell the frontend to show the Empty State
    if not has_published:
        return {"has_published": False}

    # 2. Build the live 7-day timeline for the Chart
    labels = []
    reactions_data = []
    published_data = []

    today = datetime.date.today()
    
    # Loop backward from 6 days ago to today to get a perfect 7-day rolling window
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        labels.append(target_date.strftime("%b %d")) # e.g., "Apr 04"

        # Count articles published on this exact date
        # func.date() safely strips the time off the DB timestamp
        pub_count = db.query(db_models.ArticleHistory).filter(
            db_models.ArticleHistory.user_id == current_user.id,
            db_models.ArticleHistory.status == 'Published',
            func.date(db_models.ArticleHistory.created_at) == target_date
        ).count()
        published_data.append(pub_count)

        # Get Reactions (Views + Likes) from the AnalyticsHistory table
        stat = db.query(db_models.AnalyticsHistory).filter(
            db_models.AnalyticsHistory.user_id == current_user.id,
            db_models.AnalyticsHistory.recorded_date == target_date
        ).first()

        if stat:
            reactions_data.append(stat.total_views + stat.total_likes)
        else:
            reactions_data.append(0)

    # Return the exact payload the new Chart.js setup is expecting
    return {
        "has_published": True,
        "labels": labels,
        "datasets": {
            "reactions": reactions_data,
            "published": published_data
        }
    }

@router.get("/notes", tags=["Notebook"])
async def get_notes(db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    return db.query(db_models.IdeaNote).filter(db_models.IdeaNote.user_id == current_user.id).all()

@router.post("/notes", tags=["Notebook"])
async def create_note(request: schemas.NoteRequest, db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    count = db.query(db_models.IdeaNote).filter(db_models.IdeaNote.user_id == current_user.id).count()
    if count >= 9:
        return {"error": "Notebook full."}
        
    new_note = db_models.IdeaNote(
        user_id=current_user.id, 
        title=request.title, 
        content=request.content, 
        is_bulleted=request.is_bulleted
    )
    db.add(new_note)
    db.commit()
    db.refresh(new_note)
    return new_note

# --- NEW: The Edit Route ---
@router.put("/notes/{note_id}", tags=["Notebook"])
async def update_note(note_id: int, request: schemas.NoteRequest, db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    note = db.query(db_models.IdeaNote).filter(db_models.IdeaNote.id == note_id, db_models.IdeaNote.user_id == current_user.id).first()
    if note:
        note.title = request.title
        note.content = request.content
        note.is_bulleted = request.is_bulleted
        db.commit()
        return {"status": "updated"}
    return {"error": "Note not found"}

@router.delete("/notes/{note_id}", tags=["Notebook"])
async def delete_note(note_id: int, db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    note = db.query(db_models.IdeaNote).filter(db_models.IdeaNote.id == note_id, db_models.IdeaNote.user_id == current_user.id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    db.delete(note)
    db.commit()
    return {"status": "deleted"}

@router.post("/muse", response_model=schemas.MuseResponse, tags=["Agentic AI"])
async def handle_muse_query(
    request: schemas.MuseRequest, 
    current_user: db_models.User = Depends(get_current_user)
):
    try:
        # Pass the current_user's gemini_key here!
        reply = call_the_muse(request.message, current_user.gemini_key)
        return {"reply": reply}
    except Exception as e:
        logging.error(f"Muse Route Error: {e}")
        return {"reply": "THE SPARK HAS FLICKERED. TRY AGAIN."}