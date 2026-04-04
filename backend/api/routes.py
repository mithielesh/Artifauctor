from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
import logging
import json
from datetime import timedelta
import datetime

# Database & Auth Imports
from database import get_db
from models import schemas, db_models
from auth_utils import get_current_user

# Existing services
from services.serp_scraper import fetch_top_serp_results
from services.agents import generate_seo_blog, generate_socials, call_the_muse, apply_hitl_correction
from services.validator import calculate_seo_score, calculate_humanness_score
from services.publisher import publish_to_devto, publish_to_hashnode

router = APIRouter()

# -----------------------------------------------------
# STAGE 1: THE AI PIPELINE & WORKSPACE CREATION
# -----------------------------------------------------

@router.post("/generate", response_model=schemas.BlogResponse)
async def generate_blog_endpoint(
    request: schemas.BlogRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    logging.info(f"PIPELINE START: {request.keyword} | Workspace: {request.workspace_name} | User: {current_user.email}")
    
    # 0. Check for Unique Workspace Name FIRST
    existing_ws = db.query(db_models.Workspace).filter(
        db_models.Workspace.user_id == current_user.id,
        db_models.Workspace.workspace_name == request.workspace_name
    ).first()
    
    if existing_ws:
        raise HTTPException(status_code=400, detail="Workspace name already exists. Choose a unique name.")

    # 1. BYOK Check
    if not current_user.gemini_key:
        raise HTTPException(status_code=400, detail="Gemini API Key missing in Settings.")

    try:
        # --- UPGRADED RAG-LITE INTERNAL LINKING LOOKUP ---
        # Now we grab the 'summary' to give the AI actual context!
        previous_articles = db.query(db_models.Workspace).filter(
            db_models.Workspace.user_id == current_user.id,
            db_models.Workspace.status == "Published"
        ).order_by(db_models.Workspace.id.desc()).limit(5).all()

        links_for_ai = []
        for art in previous_articles:
            url = art.devto_url or art.hashnode_url
            if url and url.strip():
                links_for_ai.append({
                    "keyword": art.keyword, 
                    "url": url.strip(),
                    "summary": art.summary # Pushing the summary into the brain
                })

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
            
        # 4. THE JUDGE: ML HYBRID VALIDATOR
        seo_score = calculate_seo_score(ai_result["blog_content"], request.keyword, request.domain)
        humanness_data = calculate_humanness_score(ai_result["blog_content"])
        
        # 5. THE STUDIO: Save as a Drafting Workspace
        new_workspace = db_models.Workspace(
            user_id=current_user.id,
            workspace_name=request.workspace_name,
            keyword=request.keyword,
            domain=request.domain,
            content=ai_result["blog_content"],
            summary=ai_result.get("summary", "A deep-dive exploration of the topic."),
            
            # --- SAVING THE METRICS TO THE DB ---
            seo_score=float(seo_score),
            naturalness=humanness_data["naturalness"], 
            readability_level=humanness_data["readability"], 
            
            status="Drafting", 
            twitter_thread=socials.get("twitter"),
            linkedin_post=socials.get("linkedin"),
            scheduled_for=request.scheduled_for 
        )
        db.add(new_workspace)
        db.commit()
        db.refresh(new_workspace)

        return schemas.BlogResponse(
            workspace_name=request.workspace_name,
            keyword=request.keyword,
            domain=request.domain,
            outline=ai_result["outline"],
            blog_content=ai_result["blog_content"],
            summary=new_workspace.summary,
            seo_score=seo_score,                    
            naturalness=humanness_data["naturalness"],          
            readability_level=humanness_data["readability"],    
            snippet_readiness="High" if "<h2>" in ai_result["blog_content"] else "Low",    
            twitter_thread=socials.get("twitter"), 
            linkedin_post=socials.get("linkedin"),
            keyword_density=0  
        )
        
    except Exception as e:
        logging.error(f"API ROUTE ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------
# MEGA UPDATE: WORKSPACE MANAGEMENT ROUTES
# -----------------------------------------------------

@router.get("/workspaces/active", response_model=list[schemas.WorkspaceResponse])
async def get_active_workspaces(db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    """Fetches all ongoing projects (Drafting, Generating, Scheduled)"""
    return db.query(db_models.Workspace).filter(
        db_models.Workspace.user_id == current_user.id,
        db_models.Workspace.status != "Published"
    ).order_by(db_models.Workspace.last_edited.desc()).all()

@router.get("/workspaces/vault", response_model=list[schemas.WorkspaceResponse])
async def get_vault_workspaces(db: Session = Depends(get_db), current_user: db_models.User = Depends(get_current_user)):
    """Fetches only Published articles (Read-Only)"""
    return db.query(db_models.Workspace).filter(
        db_models.Workspace.user_id == current_user.id,
        db_models.Workspace.status == "Published"
    ).order_by(db_models.Workspace.created_at.desc()).all()

@router.put("/workspaces/{workspace_id}/save")
async def auto_save_workspace(
    workspace_id: int, 
    req: schemas.WorkspaceSaveRequest, 
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    """The Background Auto-Save ping from The Studio editor"""
    ws = db.query(db_models.Workspace).filter(
        db_models.Workspace.id == workspace_id, 
        db_models.Workspace.user_id == current_user.id
    ).first()
    
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
    
    # Update content (SQLAlchemy automatically updates the `last_edited` timestamp!)
    ws.content = req.content
    db.commit()
    return {"status": "saved"}

@router.post("/workspaces/{workspace_id}/clone")
async def clone_to_workspace(
    workspace_id: int, 
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    """Creates an editable draft copy of a Published Vault article"""
    orig = db.query(db_models.Workspace).filter(
        db_models.Workspace.id == workspace_id, 
        db_models.Workspace.user_id == current_user.id
    ).first()
    
    if not orig:
        raise HTTPException(status_code=404, detail="Original workspace not found.")

    # Create a cloned name. If they click it multiple times, add timestamps or standard suffixes
    new_name = f"{orig.workspace_name} (Rev {datetime.datetime.now().strftime('%H%M')})"

    new_ws = db_models.Workspace(
        user_id=current_user.id,
        workspace_name=new_name,
        keyword=orig.keyword,
        domain=orig.domain,
        content=orig.content,
        summary=orig.summary,
        seo_score=orig.seo_score,
        status="Drafting", # Reset to draft so it goes to Active Workspaces!
        twitter_thread=orig.twitter_thread,
        linkedin_post=orig.linkedin_post
    )
    db.add(new_ws)
    db.commit()
    db.refresh(new_ws)
    return {"message": "Cloned successfully", "new_workspace_id": new_ws.id}

# -----------------------------------------------------
# STAGE 2: THE PUBLISHING AGENTS (Targeted Workspaces)
# -----------------------------------------------------

@router.post("/publish/devto/{workspace_id}")
async def publish_devto_route(
    workspace_id: int,
    req: schemas.PublishRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    logging.info(f"Publishing Agent: Deploying Workspace {workspace_id} to Dev.to...")
    
    if not current_user.devto_key:
        raise HTTPException(status_code=400, detail="Dev.to API Key missing in Settings.")

    # Find the EXACT workspace
    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == workspace_id, db_models.Workspace.user_id == current_user.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    url = publish_to_devto(req.title, req.content, current_user.devto_key)
    if not url:
        raise HTTPException(status_code=500, detail="Dev.to deployment failed.")
        
    ws.status = "Published"
    ws.devto_url = url
    ws.scheduled_for = None
    db.commit()

    return {"url": url}

@router.post("/publish/hashnode/{workspace_id}")
async def publish_hashnode_route(
    workspace_id: int,
    req: schemas.PublishRequest,
    db: Session = Depends(get_db),
    current_user: db_models.User = Depends(get_current_user)
):
    logging.info(f"Publishing Agent: Deploying Workspace {workspace_id} to Hashnode...")
    
    if not current_user.hashnode_token or not current_user.hashnode_pub_id:
        raise HTTPException(status_code=400, detail="Hashnode credentials missing.")

    ws = db.query(db_models.Workspace).filter(db_models.Workspace.id == workspace_id, db_models.Workspace.user_id == current_user.id).first()
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    url = publish_to_hashnode(req.title, req.content, current_user.hashnode_token, current_user.hashnode_pub_id)
    if not url:
        raise HTTPException(status_code=500, detail="Hashnode deployment failed.")
        
    ws.status = "Published"
    ws.hashnode_url = url
    ws.scheduled_for = None
    db.commit()

    return {"url": url}

# -----------------------------------------------------
# SAAS METRICS & NOTEBOOK
# -----------------------------------------------------

@router.get("/analytics", tags=["SaaS Features"])
async def get_user_analytics(
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    # Check if user has EVER published an article
    has_published = db.query(db_models.Workspace).filter(
        db_models.Workspace.user_id == current_user.id,
        db_models.Workspace.status == 'Published'
    ).first() is not None

    if not has_published:
        return {"has_published": False}

    labels = []
    reactions_data = []
    published_data = []
    today = datetime.date.today()
    
    for i in range(6, -1, -1):
        target_date = today - timedelta(days=i)
        labels.append(target_date.strftime("%b %d"))

        # Count articles published on this exact date from Workspaces
        pub_count = db.query(db_models.Workspace).filter(
            db_models.Workspace.user_id == current_user.id,
            db_models.Workspace.status == 'Published',
            func.date(db_models.Workspace.created_at) == target_date
        ).count()
        published_data.append(pub_count)

        stat = db.query(db_models.AnalyticsHistory).filter(
            db_models.AnalyticsHistory.user_id == current_user.id,
            db_models.AnalyticsHistory.recorded_date == target_date
        ).first()

        if stat:
            reactions_data.append(stat.total_views + stat.total_likes)
        else:
            reactions_data.append(0)

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
        reply = call_the_muse(request.message, current_user.gemini_key)
        return {"reply": reply}
    except Exception as e:
        logging.error(f"Muse Route Error: {e}")
        return {"reply": "THE SPARK HAS FLICKERED. TRY AGAIN."}
    
@router.post("/workspaces/{workspace_id}/correct")
async def apply_ai_correction(
    workspace_id: int, 
    req: schemas.CorrectionRequest, 
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    """Passes the current canvas text and user instructions to the HITL AI Editor."""
    ws = db.query(db_models.Workspace).filter(
        db_models.Workspace.id == workspace_id, 
        db_models.Workspace.user_id == current_user.id
    ).first()
    
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")
        
    try:
        new_text = apply_hitl_correction(req.current_content, req.instruction, current_user.gemini_key)
        # Auto-save the AI's correction to the DB immediately
        ws.content = new_text
        db.commit()
        return {"content": new_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/workspaces/{workspace_id}")
async def delete_workspace(
    workspace_id: int, 
    db: Session = Depends(get_db), 
    current_user: db_models.User = Depends(get_current_user)
):
    """The Kill Switch: Permanently deletes a workspace."""
    ws = db.query(db_models.Workspace).filter(
        db_models.Workspace.id == workspace_id, 
        db_models.Workspace.user_id == current_user.id
    ).first()
    
    if not ws:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    db.delete(ws)
    db.commit()
    return {"status": "deleted", "message": f"Workspace '{ws.workspace_name}' destroyed."}