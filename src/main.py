"""FastAPI application for web scraping API."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import router, scraper_service
from src.api.scrape_history_routes import router as history_router
from src.config import settings
from src.database.mongodb import MongoDB
from src.repositories.scrape_repository import ScrapeRepository

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown).

    Args:
        app: FastAPI application instance
    """
    # Startup
    logger.info("Application starting up...")

    # Connect to MongoDB if persistence is enabled
    if settings.ENABLE_PERSISTENCE:
        try:
            await MongoDB.connect(
                settings.MONGODB_URL,
                settings.MONGODB_DATABASE
            )
            await MongoDB.create_indexes()
            logger.info("MongoDB connected successfully")

            # Inject repository into scraper service
            db = MongoDB.get_database()
            repository = ScrapeRepository(db)
            scraper_service.repository = repository

        except Exception as e:
            logger.error(f"MongoDB connection failed: {e}")
            logger.warning("Continuing without persistence")

    yield

    # Shutdown
    logger.info("Application shutting down...")
    await scraper_service.cleanup()

    if settings.ENABLE_PERSISTENCE:
        await MongoDB.disconnect()


# Create FastAPI app
app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Web scraping API supporting both static and dynamic content",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(router)
app.include_router(history_router)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Web Scraping API",
        "version": settings.API_VERSION,
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
