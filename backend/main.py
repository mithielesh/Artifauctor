from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine
from models import db_models

# Import both our existing generation routes and the new auth routes
from api import routes, auth_routes

app = FastAPI(title="Artifauctor Engine API", version="2.0")

# This creates the SQLite artifauctor.db file and tables on startup
db_models.Base.metadata.create_all(bind=engine)

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