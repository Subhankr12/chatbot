from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import logging
import os

from app.core.config import settings
from app.models.database import get_db, engine
from app.models.models import Base
from app.api.endpoints import chat, bots, intents, organizations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    **Chatbot Platform API** - A comprehensive chatbot utility platform
    
    This API provides a full-featured chatbot platform similar to Dialogflow CX, 
    offering complete control over your chatbot infrastructure.
    
    ## Features
    
    * **Multi-tenant support** - Support multiple organizations and products
    * **Intent recognition** - Advanced NLP for understanding user intents
    * **Entity extraction** - Extract and manage custom entities
    * **Conversation management** - Maintain context across conversations
    * **Training system** - Train models with custom datasets
    * **Analytics** - Track performance and user interactions
    * **API-first design** - RESTful API for easy integration
    
    ## Authentication
    
    All endpoints require an API key in the Authorization header:
    ```
    Authorization: Bearer YOUR_API_KEY
    ```
    
    ## Quick Start
    
    1. Create an organization and get your API key
    2. Create a bot for your organization
    3. Define intents and training phrases
    4. Train your bot
    5. Start chatting!
    """,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    chat.router,
    prefix=settings.API_V1_STR,
    tags=["chat"]
)

app.include_router(
    bots.router,
    prefix=settings.API_V1_STR,
    tags=["bots"]
)

app.include_router(
    intents.router,
    prefix=settings.API_V1_STR,
    tags=["intents"]
)

app.include_router(
    organizations.router,
    prefix=settings.API_V1_STR,
    tags=["organizations"]
)

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Global exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error_code": "INTERNAL_ERROR"
        }
    )

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION
    }

# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "health_url": "/health"
    }

# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup tasks"""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Create necessary directories
    os.makedirs(settings.MODELS_DIR, exist_ok=True)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
    
    logger.info("Application startup completed")

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown tasks"""
    logger.info("Application shutting down")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )