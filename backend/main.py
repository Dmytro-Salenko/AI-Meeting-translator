import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load local .env variables if present (Render injects them as system envs directly)
load_dotenv()

# Import Routers
from app.routers.meeting_stream import router as stream_router

app = FastAPI(
    title="AI Meeting Translator API",
    description="Backend API for high-reliability live meeting transcription, translation and summary.",
    version="1.0.0"
)

# CORS Policy configuration to allow seamless connections from Flutter mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Healthcheck route for Render.com live checks
@app.get("/healthz")
async def health_check():
    return {"status": "healthy", "environment": os.getenv("ENVIRONMENT", "production")}

# Include meeting streaming and post-processing routes
app.include_router(stream_router, prefix="/api/v1")

if __name__ == "__main__":
    import uvicorn
    # Render.com provides PORT environment variable automatically
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
