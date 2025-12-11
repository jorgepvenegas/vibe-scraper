"""Base scraper interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ExtractionInfo:
    """Information about extraction attempt."""

    selector_matched: bool
    elements_found: int
    selector_used: str


@dataclass
class ScrapedData:
    """Container for scraped data."""

    content: str
    html: str
    title: str
    url: str
    screenshot: str | None = None
    extraction_info: Optional[ExtractionInfo] = field(default=None)
    parsed: Optional[list[dict[str, str]]] = field(default=None)
    table_metadata: Optional[dict] = field(default=None)


class BaseScraper(ABC):
    """Abstract base class for scrapers."""

    @abstractmethod
    async def scrape(self, url: str, **kwargs) -> ScrapedData:
        """
        Scrape content from URL.

        Args:
            url: URL to scrape
            **kwargs: Additional scraper-specific arguments

        Returns:
            ScrapedData with extracted content

        Raises:
            ScraperError: If scraping fails
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources (close connections, browsers, etc)."""
        pass
