import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from database import engine
from models import db_models
from contextlib import asynccontextmanager
from services.scheduler import scheduler # <-- Import your scheduler
import logging

# Import both our existing generation routes and the new auth routes
from api import routes, auth_routes

# Set up basic logging so you can see the scheduler start
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP LOGIC ---
    logger.info("Starting Asynchronous Scheduler & Decay Tracker...")
    scheduler.start()
    
    yield # This yields control back to FastAPI while the server runs
    
    # --- SHUTDOWN LOGIC ---
    logger.info("Shutting down Scheduler...")
    scheduler.shutdown()

app = FastAPI(title="Artifauctor Engine API", lifespan=lifespan, version="2.0")

# This creates the SQLite artifauctor.db file and tables on startup
db_models.Base.metadata.create_all(bind=engine)

# --- THE 404 INTERCEPTOR ---
# Pulls live domain from hosting, defaults to local Live Server port 5500
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:5500")

@app.exception_handler(StarletteHTTPException)
async def custom_404_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        # Bounce bad API requests to the frontend error UI
        return RedirectResponse(url=f"{FRONTEND_URL}/error.html?code=404")
    
    # If it's a 400, 422, 500, etc., return the standard JSON error
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


# Enable CORS so our Vanilla JS frontend can communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Attach Routers ---

# 1. The Gates (Login, Register, User Profile)
app.include_router(auth_routes.router, prefix="/api/v1/users", tags=["Users & Auth"])

# 2. The Engine (Generation, Publishing)
app.include_router(routes.router, prefix="/api/v1", tags=["AI Pipeline"])

@app.get("/")
async def root():
    return {"message": "Artifauctor AI Engine v2.0 is running. Ready for inputs."}