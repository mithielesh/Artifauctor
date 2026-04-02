from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
from database import SessionLocal
import models.db_models as db_models
# Assuming you have your publish functions imported here
# from services.publishers import publish_to_devto, publish_to_hashnode

def db_maintenance_job():
    """Runs periodically to publish scheduled drafts and flag decaying content."""
    db: Session = SessionLocal()
    now = datetime.utcnow()
    
    try:
        # --- 1. THE ASYNCHRONOUS SCHEDULER ---
        # Find drafts that are scheduled for right now (or earlier)
        pending_posts = db.query(db_models.ArticleHistory).filter(
            db_models.ArticleHistory.status == "Draft",
            db_models.ArticleHistory.scheduled_for <= now
        ).all()

        for post in pending_posts:
            logging.info(f"Auto-Publishing Post ID: {post.id}")
            # Note: You'll need to fetch the user's API keys here based on post.user_id
            # Example logic:
            # if post.target_platform == "hashnode":
            #     url = publish_to_hashnode(post.title, post.content, user.hashnode_token...)
            #     if url:
            #         post.status = "Published"
            #         post.hashnode_url = url
            
        # --- 2. THE CONTENT DECAY TRACKER ---
        # Find published articles older than 120 days (4 months)
        decay_threshold = now - timedelta(days=120)
        stale_posts = db.query(db_models.ArticleHistory).filter(
            db_models.ArticleHistory.status == "Published",
            db_models.ArticleHistory.created_at <= decay_threshold
        ).all()

        for post in stale_posts:
            logging.info(f"Flagging Post ID: {post.id} as STALE.")
            post.status = "Stale" # Updates the badge in the UI

        db.commit()

    except Exception as e:
        logging.error(f"Scheduler Job Failed: {e}")
        db.rollback()
    finally:
        db.close()

# Initialize the Scheduler
scheduler = BackgroundScheduler()
# Set it to run at the top of every hour
scheduler.add_job(db_maintenance_job, 'cron', minute=0)