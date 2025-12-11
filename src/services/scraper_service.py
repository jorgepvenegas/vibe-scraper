"""Scraper service for orchestrating static and dynamic scraping."""

import asyncio
from datetime import datetime
from time import time

from src.config import settings
from src.models.schemas import (
    ActionModel,
    ExtractionDebug,
    ExtractionModel,
    ScrapeMetadata,
    ScrapeRequest,
    ScrapeResponse,
)
from src.scrapers.dynamic import DynamicScraper
from src.scrapers.static import StaticScraper


class ScraperService:
    """Service for orchestrating scraping operations."""

    def __init__(self):
        """Initialize scraper service."""
        self.static_scraper = StaticScraper()
        self.dynamic_scraper = DynamicScraper()

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

            return ScrapeResponse(
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

    async def cleanup(self) -> None:
        """Cleanup all resources."""
        await asyncio.gather(
            self.static_scraper.cleanup(),
            self.dynamic_scraper.cleanup(),
            return_exceptions=True,
        )
