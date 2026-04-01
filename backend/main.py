from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router

app = FastAPI(title="Blogy AI Engine API", version="1.0")

# Enable CORS so our Vanilla JS frontend can communicate with this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, you'd restrict this to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Attach our routes
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "Blogy AI Engine is running. Ready for inputs."}