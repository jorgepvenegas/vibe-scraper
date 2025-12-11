"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class ActionModel(BaseModel):
    """Model for user actions (click, type, wait, scroll)."""

    type: Literal["click", "type", "wait", "scroll", "screenshot"]
    selector: Optional[str] = None
    value: Optional[str] = None
    wait_after: Optional[int] = Field(
        None, description="Wait time in milliseconds after action"
    )
    condition: Optional[Literal["selector", "timeout", "networkidle", "load"]] = None
    timeout: Optional[int] = Field(None, description="Timeout in milliseconds")
    amount: Optional[int] = Field(None, description="Scroll amount in pixels")

    class Config:
        json_schema_extra = {
            "example": {
                "type": "click",
                "selector": "#submit-button",
                "wait_after": 1000,
            }
        }


class ParseTableConfig(BaseModel):
    """Configuration for parsing HTML tables to JSON."""

    headers_selector: str = Field(
        "thead th", description="CSS selector for header cells"
    )
    row_selector: str = Field("tbody tr", description="CSS selector for data rows")
    cell_selector: str = Field(
        "td", description="CSS selector for data cells within rows"
    )
    header_row_index: Optional[int] = Field(
        None,
        description="If headers are in tbody, index of header row (0-based). None = use headers_selector",
    )
    skip_rows: list[int] = Field(
        default_factory=list, description="Row indices to skip (0-based)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "headers_selector": "thead th",
                "row_selector": "tbody tr",
                "cell_selector": "td",
                "header_row_index": None,
                "skip_rows": [],
            }
        }


class ExtractionModel(BaseModel):
    """Model for extraction configuration."""

    selector: str = Field(..., description="CSS selector for element to extract")
    attribute: Optional[str] = Field(
        None,
        description="HTML attribute to extract (e.g., 'href', 'src'). None = text content",
    )
    multiple: bool = Field(False, description="Extract all matching elements")
    wait_timeout: Optional[int] = Field(
        5000,
        description="In dynamic mode, wait up to this many milliseconds for selector to appear (default: 5000ms)",
    )
    inner_html: bool = Field(
        False,
        description="If true, return inner HTML (element contents). If false, return outer HTML (with element tag)",
    )
    strip: bool = Field(
        False,
        description="If true, strip HTML attributes, scripts, and styles from output (HTML output only)",
    )
    parse_table: Optional[ParseTableConfig] = Field(
        None, description="Parse extracted table to JSON"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "selector": ".content",
                "attribute": None,
                "multiple": False,
                "wait_timeout": 5000,
                "inner_html": False,
                "strip": False,
                "parse_table": None,
            }
        }


class ScrapeRequest(BaseModel):
    """Request model for scraping endpoint."""

    url: HttpUrl = Field(..., description="URL to scrape")
    mode: Literal["auto", "static", "dynamic"] = Field(
        "auto",
        description="Scraping mode: auto=intelligent choice, static=http+parser, dynamic=browser",
    )
    actions: Optional[list[ActionModel]] = Field(
        None, description="User actions to perform before extraction"
    )
    extract: Optional[ExtractionModel] = Field(
        None, description="Extraction configuration"
    )
    screenshot: bool = Field(False, description="Capture screenshot after scraping")
    output_format: Literal["json", "html", "text", "markdown"] = Field(
        "json", description="Output format for extracted data"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com",
                "mode": "auto",
                "actions": [
                    {
                        "type": "click",
                        "selector": "#submit-button",
                        "wait_after": 1000,
                    },
                    {
                        "type": "wait",
                        "condition": "selector",
                        "value": ".results",
                        "timeout": 5000,
                    },
                ],
                "extract": {
                    "selector": ".content",
                    "attribute": None,
                    "multiple": False,
                },
                "screenshot": False,
                "output_format": "json",
            }
        }


class ScrapeData(BaseModel):
    """Scraped data response."""

    content: str = Field(..., description="Extracted content")
    html: Optional[str] = Field(None, description="Full page HTML")
    title: Optional[str] = Field(None, description="Page title")
    url: str = Field(..., description="Final URL after redirects")
    parsed: Optional[list[dict[str, str]]] = Field(
        None, description="Parsed table data as JSON (if parse_table was enabled)"
    )
    table_metadata: Optional[dict] = Field(
        None, description="Metadata about parsed table (if parse_table was enabled)"
    )


class ExtractionDebug(BaseModel):
    """Debug information about extraction."""

    selector_matched: bool = Field(
        ..., description="Whether the extraction selector matched any elements"
    )
    elements_found: int = Field(
        ..., description="Number of elements matching the selector"
    )
    selector_used: str = Field(..., description="The CSS selector that was used")


class TableMetadata(BaseModel):
    """Metadata about parsed table."""

    rows_parsed: int = Field(..., description="Number of rows parsed from table")
    columns: int = Field(..., description="Number of columns in table")
    has_merged_cells: bool = Field(
        ..., description="Whether table has merged cells (colspan/rowspan)"
    )
    nested_tables_found: int = Field(
        default=0, description="Number of nested tables found in cells"
    )


class ScrapeMetadata(BaseModel):
    """Metadata about scrape operation."""

    scrape_mode: Literal["static", "dynamic"]
    duration_ms: int
    timestamp: datetime
    actions_performed: Optional[int] = None
    extracted_elements: Optional[int] = None
    extraction_debug: Optional[ExtractionDebug] = Field(
        None, description="Debug info about extraction (if selector was provided)"
    )


class ScrapeResponse(BaseModel):
    """Response model for scraping endpoint."""

    success: bool = Field(..., description="Whether scrape was successful")
    data: Optional[ScrapeData] = Field(None, description="Scraped data")
    screenshot: Optional[str] = Field(
        None, description="Base64 encoded screenshot (if requested)"
    )
    metadata: ScrapeMetadata
    error: Optional[str] = Field(None, description="Error message if unsuccessful")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "content": "Page content here",
                    "html": "<html>...</html>",
                    "title": "Example Page",
                    "url": "https://example.com",
                },
                "screenshot": None,
                "metadata": {
                    "scrape_mode": "dynamic",
                    "duration_ms": 1234,
                    "timestamp": "2025-12-09T10:00:00Z",
                    "actions_performed": 2,
                    "extracted_elements": 1,
                },
                "error": None,
            }
        }


class StoredScrape(BaseModel):
    """Model for stored scrape document from MongoDB."""

    scrape_id: str = Field(..., description="Unique ID of the stored scrape")
    request: Optional[dict] = Field(
        None, description="Original request configuration (optional)"
    )
    content: dict = Field(..., description="Extracted content from scrape")
    metadata: dict = Field(..., description="Metadata about the scrape")
    created_at: datetime = Field(..., description="When the scrape was stored")
    updated_at: datetime = Field(..., description="When the scrape was last updated")


class ScrapeQueryResponse(BaseModel):
    """Response model for scrape queries."""

    total: int = Field(..., description="Total number of results matching query")
    limit: int = Field(..., description="Limit applied to query")
    offset: int = Field(..., description="Offset applied to query")
    results: list[StoredScrape] = Field(..., description="Array of scrape results")


class ScrapeStatistics(BaseModel):
    """Statistics for dashboard."""

    mode: str = Field(..., description="Scrape mode (static or dynamic)")
    success: bool = Field(..., description="Whether scrapes were successful")
    count: int = Field(..., description="Number of scrapes")
    avg_duration_ms: float = Field(
        ..., description="Average scrape duration in milliseconds"
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: Literal["healthy", "degraded", "unhealthy"]
    version: str
    scrapers: dict[str, Literal["available", "unavailable"]]
