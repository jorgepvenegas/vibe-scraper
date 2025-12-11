"""Dynamic content scraper using Playwright."""

import base64

from playwright.async_api import Browser, async_playwright, Page
from bs4 import BeautifulSoup

from src.config import settings
from src.models.schemas import ActionModel, ExtractionModel
from src.scrapers.base import BaseScraper, ScrapedData, ExtractionInfo


class DynamicScraper(BaseScraper):
    """Scraper for dynamic/JavaScript-rendered content using Playwright."""

    def __init__(self):
        """Initialize dynamic scraper."""
        self.browser: Browser | None = None
        self.playwright = None

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

    async def _ensure_browser(self) -> Browser:
        """Ensure browser instance is initialized."""
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                **settings.PLAYWRIGHT_LAUNCH_ARGS
            )
        return self.browser

    async def scrape(
        self,
        url: str,
        actions: list[ActionModel] | None = None,
        extract: ExtractionModel | None = None,
        output_format: str = "json",
        screenshot: bool = False,
        **kwargs,
    ) -> ScrapedData:
        """
        Scrape dynamic content using Playwright.

        Args:
            url: URL to scrape
            actions: User actions to perform
            extract: Extraction configuration
            output_format: Output format
            screenshot: Whether to capture screenshot
            **kwargs: Additional arguments

        Returns:
            ScrapedData with extracted content

        Raises:
            Exception: If scraping fails
        """
        browser = await self._ensure_browser()
        page = await browser.new_page()

        try:
            # Navigate to URL
            await page.goto(url, wait_until="networkidle", timeout=settings.PLAYWRIGHT_TIMEOUT)

            # Perform actions if provided
            actions_performed = 0
            if actions:
                for action in actions:
                    await self._perform_action(page, action)
                    actions_performed += 1

            # Wait for extraction selector to appear if provided
            if extract and extract.selector:
                try:
                    await page.wait_for_selector(
                        extract.selector,
                        timeout=extract.wait_timeout or settings.PLAYWRIGHT_TIMEOUT
                    )
                except Exception as e:
                    raise Exception(
                        f"Extraction failed: selector '{extract.selector}' did not appear "
                        f"within {extract.wait_timeout or settings.PLAYWRIGHT_TIMEOUT}ms. "
                        f"Possible issues: (1) Element is created by AJAX after action, add a wait action, "
                        f"(2) Selector syntax is incorrect, (3) Element structure changed"
                    ) from e

            # Get page content
            html_content = await page.content()
            page_url = page.url
            title = await page.title()

            # Extract content
            soup = BeautifulSoup(html_content, "lxml")
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

            # Capture screenshot if requested
            screenshot_data = None
            if screenshot and settings.ENABLE_SCREENSHOTS:
                screenshot_bytes = await page.screenshot()
                screenshot_data = base64.b64encode(screenshot_bytes).decode()

            return ScrapedData(
                content=content,
                html=html_content,
                title=title,
                url=page_url,
                screenshot=screenshot_data,
                extraction_info=extraction_info,
                parsed=parsed_data,
                table_metadata=table_metadata,
            )

        finally:
            await page.close()

    async def _perform_action(self, page: Page, action: ActionModel) -> None:
        """
        Perform a user action on the page.

        Args:
            page: Playwright page object
            action: Action to perform
        """
        if action.type == "click":
            if action.selector:
                await page.click(action.selector)
                if action.wait_after:
                    await page.wait_for_timeout(action.wait_after)

        elif action.type == "type":
            if action.selector and action.value:
                await page.fill(action.selector, action.value)
                if action.wait_after:
                    await page.wait_for_timeout(action.wait_after)

        elif action.type == "wait":
            await self._wait_for_condition(page, action)

        elif action.type == "scroll":
            if action.selector:
                await page.locator(action.selector).scroll_into_view_if_needed()
            elif action.amount:
                await page.evaluate(f"window.scrollBy(0, {action.amount})")
            if action.wait_after:
                await page.wait_for_timeout(action.wait_after)

        elif action.type == "screenshot":
            # This is a marker for when to take screenshot (handled in scrape method)
            if action.wait_after:
                await page.wait_for_timeout(action.wait_after)

    async def _wait_for_condition(self, page: Page, action: ActionModel) -> None:
        """
        Wait for a condition to be met.

        Args:
            page: Playwright page object
            action: Action with wait condition
        """
        timeout = action.timeout or settings.PLAYWRIGHT_TIMEOUT

        if action.condition == "selector":
            if action.value:
                await page.wait_for_selector(action.value, timeout=timeout)

        elif action.condition == "networkidle":
            await page.wait_for_load_state("networkidle", timeout=timeout)

        elif action.condition == "load":
            await page.wait_for_load_state("load", timeout=timeout)

        elif action.condition == "timeout":
            await page.wait_for_timeout(timeout)

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

    def _format_element(self, element, attribute: str | None, output_format: str, inner_html: bool = False, strip: bool = False) -> str:
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
            return content
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
        """Close browser and cleanup resources."""
        if self.browser:
            await self.browser.close()
            self.browser = None
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
