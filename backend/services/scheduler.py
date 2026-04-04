from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session

# Database & Models
from database import SessionLocal
import models.db_models as db_models

# Publisher Agents
from services.publisher import publish_to_devto, publish_to_hashnode

def db_maintenance_job():
    """Runs periodically to publish scheduled drafts and flag decaying content."""
    db: Session = SessionLocal()
    
    # THE TIMEZONE FIX: 
    # Get current UTC time, but strip the timezone info so it becomes "naive".
    # This allows it to perfectly compare against SQLite's naive datetime columns.
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    
    try:
        # --- 1. THE ASYNCHRONOUS SCHEDULER ---
        # Find workspaces that have a schedule date that has passed, but aren't published yet
        pending_posts = db.query(db_models.Workspace).filter(
            db_models.Workspace.status != "Published",
            db_models.Workspace.scheduled_for != None,
            db_models.Workspace.scheduled_for <= now
        ).all()

        for post in pending_posts:
            logging.info(f"Scheduler Triggered: Auto-Publishing Workspace ID: {post.id}")
            
            # 1a. Securely fetch the specific user's API Keys
            user = db.query(db_models.User).filter(db_models.User.id == post.user_id).first()
            if not user:
                continue

            published_any = False
            title = post.workspace_name # Using the Workspace Name as the Title

            # 1b. Deploy to Dev.to if they have a key
            if user.devto_key:
                devto_url = publish_to_devto(title, post.content, user.devto_key)
                if devto_url:
                    post.devto_url = devto_url
                    published_any = True

            # 1c. Deploy to Hashnode if they have keys
            if user.hashnode_token and user.hashnode_pub_id:
                hashnode_url = publish_to_hashnode(title, post.content, user.hashnode_token, user.hashnode_pub_id)
                if hashnode_url:
                    post.hashnode_url = hashnode_url
                    published_any = True

            # 1d. Finalize the state change
            if published_any:
                post.status = "Published"
                post.scheduled_for = None # Clear the schedule so it doesn't trigger again
                logging.info(f"Workspace {post.id} successfully auto-published!")
            else:
                logging.warning(f"Workspace {post.id} failed to auto-publish. Check API keys.")
                # We strip the schedule time so it doesn't get stuck in an infinite retry loop
                post.scheduled_for = None 
            
        # --- 2. THE CONTENT DECAY TRACKER ---
        # Find published articles that haven't been edited in 120 days
        decay_threshold = now - timedelta(days=120)
        stale_posts = db.query(db_models.Workspace).filter(
            db_models.Workspace.status == "Published",
            db_models.Workspace.last_edited <= decay_threshold
        ).all()

        for post in stale_posts:
            logging.info(f"Flagging Workspace ID: {post.id} as STALE due to decay.")
            post.status = "Stale" # Updates the badge in the UI

        db.commit()

    except Exception as e:
        logging.error(f"Scheduler Job Failed: {e}")
        db.rollback()
    finally:
        db.close()

# Initialize the Scheduler
scheduler = BackgroundScheduler()

# For Testing/MVP: We run this every 1 minute so you can actually test the scheduling feature fast.
# In Production, change this back to: scheduler.add_job(db_maintenance_job, 'cron', minute=0)
scheduler.add_job(db_maintenance_job, 'interval', minutes=1)