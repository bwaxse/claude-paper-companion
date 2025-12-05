"""
Main FastAPI application for Paper Companion.
"""

import logging
import time
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html
from fastapi.openapi.utils import get_openapi
from starlette.exceptions import HTTPException as StarletteHTTPException

from .routes import sessions, queries, zotero
from ..core.database import init_database


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Handles:
    - Database initialization on startup
    - Cleanup on shutdown
    """
    # Startup
    logger.info("Starting Paper Companion API...")
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Paper Companion API...")


# Create FastAPI app
app = FastAPI(
    title="Paper Companion API",
    description="AI-powered academic paper analysis and conversation",
    version="0.1.0",
    lifespan=lifespan
)


# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log all requests with timing information.

    Logs:
    - HTTP method and path
    - Client IP
    - Response status code
    - Request duration
    """
    start_time = time.time()

    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )

    # Process request
    try:
        response = await call_next(request)
    except Exception as e:
        logger.error(f"Request failed: {e}")
        raise

    # Log response
    duration = time.time() - start_time
    logger.info(
        f"Response: {response.status_code} "
        f"for {request.method} {request.url.path} "
        f"({duration:.3f}s)"
    )

    return response


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Error handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Handle HTTP exceptions with consistent JSON response format.

    Returns:
        JSON response with error details
    """
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail} "
        f"for {request.method} {request.url.path}"
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.status_code,
                "message": exc.detail,
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Handle request validation errors with detailed error messages.

    Returns:
        JSON response with validation error details
    """
    logger.warning(
        f"Validation error for {request.method} {request.url.path}: {exc.errors()}"
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": {
                "code": 422,
                "message": "Validation error",
                "details": exc.errors(),
                "path": str(request.url.path)
            }
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    Handle unexpected exceptions with generic error response.

    Returns:
        JSON response with generic error message
    """
    logger.error(
        f"Unhandled exception for {request.method} {request.url.path}: {exc}",
        exc_info=True
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": 500,
                "message": "Internal server error",
                "path": str(request.url.path)
            }
        }
    )


# Include routers BEFORE mounting static files
# This ensures /api/*, /docs, /redoc, /openapi.json take priority
app.include_router(sessions.router)
app.include_router(queries.router)
app.include_router(zotero.router)


# Serve static frontend files
# Look for frontend/dist directory relative to project root
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    logger.info(f"Serving static frontend from {frontend_dist}")
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
else:
    logger.warning(f"Frontend dist directory not found at {frontend_dist}")

    @app.get("/")
    async def root():
        """Root endpoint - API health check."""
        return {
            "status": "ok",
            "service": "Paper Companion API",
            "version": "0.1.0",
            "note": "Frontend not available - run 'npm run build' in frontend/"
        }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Custom API docs endpoints (before static file mounting)
@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui():
    """Swagger UI documentation."""
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title="Paper Companion API - Swagger UI"
    )


@app.get("/redoc", include_in_schema=False)
async def custom_redoc():
    """ReDoc documentation."""
    return get_redoc_html(
        openapi_url="/openapi.json",
        title="Paper Companion API - ReDoc"
    )


@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_schema():
    """OpenAPI schema endpoint."""
    return get_openapi(
        title="Paper Companion API",
        version="0.1.0",
        description="AI-powered academic paper analysis and conversation",
        routes=app.routes
    )
