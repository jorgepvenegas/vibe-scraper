"""Scraper service for orchestrating static and dynamic scraping."""

import asyncio
import logging
from datetime import datetime
from time import time
from typing import Optional

from src.config import settings
from src.models.schemas import (
    ActionModel,
    ExtractionDebug,
    ExtractionModel,
    ScrapeMetadata,
    ScrapeRequest,
    ScrapeResponse,
)
from src.repositories.scrape_repository import ScrapeRepository
from src.scrapers.dynamic import DynamicScraper
from src.scrapers.static import StaticScraper

logger = logging.getLogger(__name__)


class ScraperService:
    """Service for orchestrating scraping operations."""

    def __init__(self, repository: Optional[ScrapeRepository] = None):
        """Initialize scraper service.

        Args:
            repository: Optional repository for persisting scrape results
        """
        self.static_scraper = StaticScraper()
        self.dynamic_scraper = DynamicScraper()
        self.repository = repository

    async def scrape(self, request: ScrapeRequest) -> ScrapeResponse:
        """
        Perform scraping based on request configuration.

        Args:
            request: Scraping request with URL and options

        Returns:
            ScrapeResponse with results

        Raises:
            Exception: Conversion to error in response
        """
        start_time = time()

        try:
            # Determine scraping mode
            mode = self._determine_mode(request.mode)

            # Perform scraping
            if mode == "dynamic":
                scraped_data = await self.dynamic_scraper.scrape(
                    url=str(request.url),
                    actions=request.actions,
                    extract=request.extract,
                    output_format=request.output_format,
                    screenshot=request.screenshot,
                )
            else:  # static
                scraped_data = await self.static_scraper.scrape(
                    url=str(request.url),
                    extract=request.extract,
                    output_format=request.output_format,
                )

            # Calculate duration
            duration_ms = int((time() - start_time) * 1000)

            # Extract debug info if available
            extraction_debug = None
            if scraped_data.extraction_info:
                extraction_debug = ExtractionDebug(
                    selector_matched=scraped_data.extraction_info.selector_matched,
                    elements_found=scraped_data.extraction_info.elements_found,
                    selector_used=scraped_data.extraction_info.selector_used,
                )

            # Check if extraction failed
            if (
                request.extract
                and scraped_data.extraction_info
                and not scraped_data.extraction_info.selector_matched
            ):
                return ScrapeResponse(
                    success=False,
                    data=None,
                    screenshot=None,
                    metadata=ScrapeMetadata(
                        scrape_mode=mode,
                        duration_ms=duration_ms,
                        timestamp=datetime.now(),
                        actions_performed=len(request.actions)
                        if request.actions
                        else 0,
                        extracted_elements=0,
                        extraction_debug=extraction_debug,
                    ),
                    error=f"Extraction failed: selector '{scraped_data.extraction_info.selector_used}' matched 0 elements. "
                    f"Possible issues: (1) Element hasn't appeared - try adding a wait action, "
                    f"(2) Selector syntax is incorrect, (3) Element structure changed",
                )

            # Count extracted elements
            extracted_elements = None
            if request.extract and scraped_data.extraction_info:
                extracted_elements = scraped_data.extraction_info.elements_found

            response = ScrapeResponse(
                success=True,
                data={
                    "content": scraped_data.content,
                    "html": scraped_data.html
                    if not request.extract
                    else None,  # Exclude full HTML if extraction was requested
                    "title": scraped_data.title,
                    "url": scraped_data.url,
                    "parsed": scraped_data.parsed,
                    "table_metadata": scraped_data.table_metadata,
                },
                screenshot=scraped_data.screenshot,
                metadata=ScrapeMetadata(
                    scrape_mode=mode,
                    duration_ms=duration_ms,
                    timestamp=datetime.now(),
                    actions_performed=len(request.actions) if request.actions else 0,
                    extracted_elements=extracted_elements,
                    extraction_debug=extraction_debug,
                ),
                error=None,
            )

            # Store result if persistence is enabled
            if settings.ENABLE_PERSISTENCE and self.repository:
                try:
                    await self._store_result(request, response)
                except Exception as e:
                    # Log error but don't fail the scrape
                    logger.error(f"Failed to store scrape result: {e}")

            return response

        except Exception as e:
            duration_ms = int((time() - start_time) * 1000)
            return ScrapeResponse(
                success=False,
                data=None,
                screenshot=None,
                metadata=ScrapeMetadata(
                    scrape_mode="dynamic",  # Default when error
                    duration_ms=duration_ms,
                    timestamp=datetime.now(),
                    actions_performed=0,
                    extracted_elements=0,
                ),
                error=str(e),
            )

    def _determine_mode(self, requested_mode: str) -> str:
        """
        Determine actual scraping mode.

        Args:
            requested_mode: Mode requested by user (auto, static, dynamic)

        Returns:
            Actual mode to use (static or dynamic)
        """
        if requested_mode in ("static", "dynamic"):
            return requested_mode

        # Auto mode - default to dynamic if actions requested, else static
        # In a real implementation, you might check page complexity
        return "dynamic"

    async def _store_result(
        self, request: ScrapeRequest, response: ScrapeResponse
    ) -> None:
        """Store scrape result in MongoDB.

        Args:
            request: The original scrape request
            response: The scrape response with results
        """
        document = {
            # "request": {
            #     "url": str(request.url),
            #     "mode": request.mode,
            #     "actions": [action.model_dump() for action in request.actions] if request.actions else [],
            #     "extract": request.extract.model_dump() if request.extract else None,
            #     "output_format": request.output_format,
            #     "screenshot_requested": request.screenshot
            # },
            "content": {
                "extracted_text": response.data.content if response.data else None,
                "title": response.data.title if response.data else None,
                "final_url": response.data.url if response.data else None,
                "parsed_table": response.data.parsed if response.data else None,
                "table_metadata": response.data.table_metadata
                if response.data
                else None,
            },
            "metadata": {
                "scrape_mode": response.metadata.scrape_mode,
                "duration_ms": response.metadata.duration_ms,
                "timestamp": response.metadata.timestamp,
                "actions_performed": response.metadata.actions_performed,
                "extracted_elements": response.metadata.extracted_elements,
                "success": response.success,
                "error": response.error,
                "extraction_debug": response.metadata.extraction_debug.model_dump()
                if response.metadata.extraction_debug
                else None,
            },
        }

        await self.repository.create(document)

    async def cleanup(self) -> None:
        """Cleanup all resources."""
        await asyncio.gather(
            self.static_scraper.cleanup(),
            self.dynamic_scraper.cleanup(),
            return_exceptions=True,
        )
