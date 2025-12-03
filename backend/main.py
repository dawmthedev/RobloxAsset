"""
Main FastAPI application for the 3D Asset Generation Pipeline.

This application provides a complete API for:
- Tier 1: 2D concept image generation using OpenAI DALL-E
- Tier 2: 3D prototype generation using Shap-E
- Tier 3: High-quality final 3D model generation using Meshy API

Run with: uvicorn main:app --reload --host 0.0.0.0 --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from config import CORS_ORIGINS, API_HOST, API_PORT, STORAGE_DIR
from database import init_db

# Import routers
from routers import generate_2d, refine_2d, shap_e, meshy, gallery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Initializes database and performs startup tasks.
    """
    # Startup
    logger.info("Starting 3D Asset Generation Pipeline API...")
    init_db()
    logger.info("Database initialized successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down API...")


# Create FastAPI application
app = FastAPI(
    title="3D Asset Generation Pipeline",
    description="""
    A 3-tier 3D asset generation pipeline API.
    
    ## Tiers
    
    - **Tier 1 - 2D Concepts**: Generate clean 2D concept images using OpenAI DALL-E
    - **Tier 2 - 3D Prototypes**: Convert 2D images to 3D prototypes using Shap-E
    - **Tier 3 - Final Models**: Generate high-quality 3D models using Meshy API
    
    ## Workflow
    
    1. Generate a 2D concept image with `/generate/2d`
    2. Optionally refine the image with `/refine/2d`
    3. Create a 3D prototype with `/generate/shap_e`
    4. Save the prototype to gallery with `/gallery/save`
    5. Generate final high-quality model with `/generate/meshy`
    """,
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for storage access
app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")

# Include routers
app.include_router(generate_2d.router)
app.include_router(refine_2d.router)
app.include_router(shap_e.router)
app.include_router(meshy.router)
app.include_router(gallery.router)


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - API health check.
    
    Returns:
        API status and version information
    """
    return {
        "status": "healthy",
        "service": "3D Asset Generation Pipeline",
        "version": "1.0.0",
        "endpoints": {
            "2d_generation": "/generate/2d",
            "2d_refinement": "/refine/2d",
            "shap_e_prototype": "/generate/shap_e",
            "meshy_final": "/generate/meshy",
            "gallery": "/gallery",
        },
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Detailed health check endpoint.
    
    Returns:
        Health status of all services
    """
    health_status = {
        "api": "healthy",
        "database": "unknown",
        "openai": "unknown",
        "shap_e": "unknown",
        "meshy": "unknown",
    }
    
    # Check database
    try:
        from database import SessionLocal
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
        health_status["database"] = "healthy"
    except Exception as e:
        health_status["database"] = f"unhealthy: {str(e)}"
    
    # Check OpenAI
    try:
        from services.openai_service import get_openai_service
        service = get_openai_service()
        if service.validate_api_key():
            health_status["openai"] = "healthy"
        else:
            health_status["openai"] = "unhealthy: invalid API key"
    except Exception as e:
        health_status["openai"] = f"not configured: {str(e)}"
    
    # Check Shap-E
    try:
        from services.shap_e_service import get_shap_e_service
        service = get_shap_e_service()
        if service.is_available():
            health_status["shap_e"] = "available"
        else:
            health_status["shap_e"] = "not installed"
    except Exception as e:
        health_status["shap_e"] = f"error: {str(e)}"
    
    # Check Meshy
    try:
        from services.meshy_service import get_meshy_service
        service = get_meshy_service()
        if service.validate_api_key():
            health_status["meshy"] = "healthy"
        else:
            health_status["meshy"] = "unhealthy: invalid API key"
    except Exception as e:
        health_status["meshy"] = f"not configured: {str(e)}"
    
    return health_status


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Global exception handler for unhandled errors.
    
    Args:
        request: The incoming request
        exc: The exception that was raised
        
    Returns:
        JSON error response
    """
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc),
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=API_HOST,
        port=API_PORT,
        reload=True,
    )
