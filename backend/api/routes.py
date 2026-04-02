# backend/api/routes.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
import json

# New Database & Auth Imports
from database import get_db
from models import schemas, db_models
from auth_utils import get_current_user

# Your existing services
from services.serp_scraper import fetch_top_serp_results
from services.agents import generate_seo_blog, generate_socials
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