from fastapi import APIRouter, HTTPException
from models.schemas import BlogRequest, BlogResponse, PublishRequest
from services.serp_scraper import fetch_top_serp_results
from services.agents import generate_seo_blog
from services.validator import calculate_seo_metrics
from services.publisher import publish_to_devto, publish_to_hashnode
import logging

router = APIRouter()

# --- STAGE 1: THE AI PIPELINE ---

@router.post("/generate", response_model=BlogResponse)
async def generate_blog_endpoint(request: BlogRequest):
    """
    Executes the research, generation, and validation pipeline.
    Returns the blog and SEO metrics to the frontend for editorial review.
    """
    logging.info(f"PIPELINE START: {request.keyword} | Domain: {request.domain}")
    
    try:
        # 1. THE EYES: Competitive SERP Research
        serp_data = fetch_top_serp_results(request.keyword, max_results=4)
        if not serp_data:
            raise HTTPException(status_code=500, detail="SERP Scraping Failed.")
            
        # 2. THE BRAIN: Enterprise-Grade Generation (PAS Framework)
        ai_result = generate_seo_blog(request.keyword, serp_data, request.domain)
        if not ai_result:
            raise HTTPException(status_code=500, detail="AI Generation Failed.")
            
        # 3. THE JUDGE: Heuristic SEO & Naturalness Validation
        metrics = calculate_seo_metrics(request.keyword, ai_result["blog_content"], request.domain)
        
        logging.info(f"PIPELINE COMPLETE: SEO Score {metrics['seo_score']}/100")

        # 4. Return Data to UI for Editorial Approval
        return BlogResponse(
            keyword=request.keyword,
            domain=request.domain,
            outline=ai_result["outline"],
            blog_content=ai_result["blog_content"],
            seo_score=metrics["seo_score"],
            keyword_density=metrics["keyword_density"],
            naturalness=metrics["naturalness"],
            snippet_readiness=metrics["snippet_readiness"],
            readability_level=metrics["readability_level"]
        )
        
    except Exception as e:
        logging.error(f"API ROUTE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# --- STAGE 2: THE PUBLISHING AGENTS (HITL) ---

@router.post("/publish/devto")
async def publish_devto_route(req: PublishRequest):
    """Triggered manually by the 'Approve' button for Dev.to"""
    logging.info(f"Publishing Agent: Deploying to Dev.to...")
    url = publish_to_devto(req.title, req.content)
    if not url:
        raise HTTPException(status_code=500, detail="Dev.to deployment failed.")
    return {"url": url}

@router.post("/publish/hashnode")
async def publish_hashnode_route(req: PublishRequest):
    """Triggered manually by the 'Approve' button for Hashnode"""
    logging.info(f"Publishing Agent: Deploying to Hashnode...")
    url = publish_to_hashnode(req.title, req.content)
    if not url:
        raise HTTPException(status_code=500, detail="Hashnode deployment failed.")
    return {"url": url}