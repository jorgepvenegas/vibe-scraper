"""API routes for the scraping service."""

from fastapi import APIRouter, HTTPException, status

from src.config import settings
from src.models.schemas import (
    HealthResponse,
    ScrapeRequest,
    ScrapeResponse,
)
from src.services.scraper_service import ScraperService

router = APIRouter()

# Initialize scraper service at module level
scraper_service = ScraperService()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape(request: ScrapeRequest) -> ScrapeResponse:
    """
    Scrape content from a URL.

    This endpoint accepts a URL and optional scraping configuration including:
    - User actions (click, type, wait, scroll)
    - Content extraction rules
    - Output format (json, html, text, markdown)
    - Screenshot capture

    Args:
        request: ScrapeRequest with URL and options

    Returns:
        ScrapeResponse with scraped data and metadata

    Raises:
        HTTPException: For invalid requests or scraping errors
    """
    try:
        # Validate URL length
        if len(str(request.url)) > settings.MAX_URL_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL exceeds maximum length of {settings.MAX_URL_LENGTH}",
            )

        # Validate URL scheme
        url_scheme = (
            str(request.url).split("://")[0] if "://" in str(request.url) else ""
        )
        if url_scheme not in settings.ALLOWED_SCHEMES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"URL scheme '{url_scheme}' not allowed. Allowed: {settings.ALLOWED_SCHEMES}",
            )

        # Validate mode
        if request.mode not in ("auto", "static", "dynamic"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid mode. Must be 'auto', 'static', or 'dynamic'",
            )

        # Check if dynamic mode is disabled
        if request.mode == "dynamic" and not settings.ENABLE_DYNAMIC_MODE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Dynamic scraping is not enabled",
            )

        # Check if static mode is disabled
        if request.mode == "static" and not settings.ENABLE_STATIC_MODE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Static scraping is not enabled",
            )

        # Perform scraping
        response = await scraper_service.scrape(request)

        # Return response even if scraping failed (error info in response)
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unexpected error: {str(e)}",
        ) from e


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Health check endpoint.

    Returns:
        HealthResponse with service status and available scrapers
    """
    return HealthResponse(
        status="healthy",
        version=settings.API_VERSION,
        scrapers={
            "static": "available" if settings.ENABLE_STATIC_MODE else "unavailable",
            "dynamic": "available" if settings.ENABLE_DYNAMIC_MODE else "unavailable",
        },
    )
