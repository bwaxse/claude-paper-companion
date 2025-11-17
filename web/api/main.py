"""
Main FastAPI application for Paper Companion.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import sessions, queries, zotero


# Create FastAPI app
app = FastAPI(
    title="Paper Companion API",
    description="AI-powered academic paper analysis and conversation",
    version="0.1.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router)
app.include_router(queries.router)
app.include_router(zotero.router)


@app.get("/")
async def root():
    """Root endpoint - API health check."""
    return {
        "status": "ok",
        "service": "Paper Companion API",
        "version": "0.1.0"
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
