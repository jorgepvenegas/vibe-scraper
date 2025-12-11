"""Static HTML scraper using httpx and BeautifulSoup."""

import httpx
from bs4 import BeautifulSoup

from src.config import settings
from src.models.schemas import ExtractionModel
from src.scrapers.base import BaseScraper, ScrapedData, ExtractionInfo


class StaticScraper(BaseScraper):
    """Scraper for static HTML content using HTTP requests."""

    def __init__(self):
        """Initialize static scraper."""
        self.client = httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": settings.DEFAULT_USER_AGENT},
        )

    def _strip_html(self, html_string: str) -> str:
        """
        Strip HTML attributes, scripts, and styles from HTML.

        Args:
            html_string: HTML string to strip

        Returns:
            Cleaned HTML string with no attributes or scripts
        """
        soup = BeautifulSoup(html_string, "lxml")

        # Remove script and style tags completely
        for tag in soup.find_all(["script", "style"]):
            tag.decompose()

        # Remove all attributes from remaining tags
        for tag in soup.find_all(True):
            tag.attrs = {}

        # Use formatter=None to minimize whitespace, then remove any remaining newlines
        html_output = str(soup.encode(formatter=None), "utf-8")
        return html_output.replace("\n", "")

    async def scrape(
        self,
        url: str,
        extract: ExtractionModel | None = None,
        output_format: str = "json",
        **kwargs,
    ) -> ScrapedData:
        """
        Scrape static HTML content.

        Args:
            url: URL to scrape
            extract: Extraction configuration
            output_format: Output format (json, html, text, markdown)
            **kwargs: Additional arguments

        Returns:
            ScrapedData with extracted content

        Raises:
            httpx.RequestError: If HTTP request fails
        """
        # Fetch the page
        response = await self.client.get(url)
        response.raise_for_status()

        html_content = response.text
        final_url = str(response.url)

        # Parse HTML
        soup = BeautifulSoup(html_content, "lxml")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""

        # Extract content based on configuration
        content, extraction_info = self._extract_content(soup, extract, output_format)

        # Parse table if requested
        parsed_data = None
        table_metadata = None
        if extract and extract.parse_table and extraction_info and extraction_info.selector_matched:
            from src.scrapers.table_parser import TableParser

            parser = TableParser()
            try:
                parsed_data, table_metadata = parser.parse(content, extract.parse_table)
            except Exception as e:
                # Log parsing error but don't fail the whole request
                pass

        return ScrapedData(
            content=content,
            html=html_content,
            title=title,
            url=final_url,
            screenshot=None,
            extraction_info=extraction_info,
            parsed=parsed_data,
            table_metadata=table_metadata,
        )

    def _extract_content(
        self, soup: BeautifulSoup, extract: ExtractionModel | None, output_format: str
    ) -> tuple[str, ExtractionInfo | None]:
        """
        Extract content from BeautifulSoup object.

        Args:
            soup: BeautifulSoup object
            extract: Extraction configuration
            output_format: Output format

        Returns:
            Tuple of (extracted content, extraction_info)
        """
        if not extract:
            # Return full content based on format
            if output_format == "html":
                return str(soup), None
            elif output_format == "markdown":
                # Simple markdown conversion - extract text with some structure
                return soup.get_text(separator="\n", strip=True), None
            else:  # json or text
                return soup.get_text(separator=" ", strip=True), None

        # Extract specific element(s)
        elements = soup.select(extract.selector)
        extraction_info = ExtractionInfo(
            selector_matched=len(elements) > 0,
            elements_found=len(elements),
            selector_used=extract.selector,
        )

        if not elements:
            return "", extraction_info

        if extract.multiple:
            content = self._format_elements(elements, extract.attribute, output_format, extract.inner_html, extract.strip)
        else:
            content = self._format_element(elements[0], extract.attribute, output_format, extract.inner_html, extract.strip)

        return content, extraction_info

    def _format_element(
        self, element, attribute: str | None, output_format: str, inner_html: bool = False, strip: bool = False
    ) -> str:
        """Format a single element based on output format."""
        if attribute:
            content = element.get(attribute, "")
        else:
            content = element.get_text(separator=" ", strip=True)

        if output_format == "html":
            if inner_html:
                # Return inner HTML (element contents without the element tag)
                html_output = element.decode_contents()
            else:
                # Return outer HTML (element with its tag)
                html_output = str(element)

            # Apply stripping if requested
            if strip:
                html_output = self._strip_html(html_output)

            return html_output
        elif output_format == "markdown":
            return content  # Simplified markdown
        else:  # json or text
            return str(content)

    def _format_elements(
        self, elements, attribute: str | None, output_format: str, inner_html: bool = False, strip: bool = False
    ) -> str:
        """Format multiple elements based on output format."""
        if attribute:
            results = [element.get(attribute, "") for element in elements]
        else:
            results = [
                element.get_text(separator=" ", strip=True) for element in elements
            ]

        if output_format == "html":
            if inner_html:
                html_output = "".join(e.decode_contents() for e in elements)
            else:
                html_output = "".join(str(e) for e in elements)

            # Apply stripping if requested
            if strip:
                html_output = self._strip_html(html_output)

            return html_output
        elif output_format == "markdown":
            return "\n".join(results)
        else:  # json or text
            return "\n".join(str(r) for r in results)

    async def cleanup(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()
