# Asistencia C�mara - Web Scraping API

A modern FastAPI-based web scraping service that supports both static and dynamic content extraction. The API intelligently handles JavaScript-rendered pages through Playwright while offering lightweight HTTP-based scraping for static content.

## Features

- **Dual-mode scraping**: Automatically choose between static (httpx) and dynamic (Playwright) scraping
- **User interactions**: Simulate clicks, form fills, and scrolling before content extraction
- **Wait conditions**: Wait for specific elements, network idle, or page load states
- **Screenshots**: Capture page screenshots at any point
- **Multiple output formats**: JSON, HTML, plain text, or markdown
- **Content extraction**: CSS selector-based content extraction with single or multiple element support
- **Table parsing**: Extract HTML tables into structured JSON arrays with support for merged cells, nested tables, and custom selectors
- **HTML cleaning**: Strip attributes, scripts, and styles while preserving semantic structure
- **Async-first**: Built with async/await for high performance
- **Production-ready**: Comprehensive error handling and resource management

## Installation

### Prerequisites

- Python 3.13 or higher
- `uv` package manager

### Setup

1. **Clone/navigate to project**:

```bash
cd asistencia-camara
```

2. **Create and activate virtual environment** (using uv):

```bash
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies**:

```bash
uv sync
```

4. **Install Playwright browsers**:

```bash
playwright install chromium
```

## Usage

### Start the API server

```bash
python -m uvicorn src.main:app --reload
```

The API will be available at `http://localhost:8000`

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Basic Examples

#### 1. Simple static page scraping

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "mode": "static",
    "extract": {
      "selector": "h1",
      "attribute": null,
      "multiple": false
    }
  }'
```

#### 2. Dynamic content with user interaction

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/search",
    "mode": "dynamic",
    "actions": [
      {
        "type": "type",
        "selector": "input[name=\"query\"]",
        "value": "python programming"
      },
      {
        "type": "click",
        "selector": "button[type=\"submit\"]",
        "wait_after": 1000
      },
      {
        "type": "wait",
        "condition": "selector",
        "value": ".results",
        "timeout": 5000
      }
    ],
    "extract": {
      "selector": ".result-item",
      "attribute": null,
      "multiple": true
    }
  }'
```

#### 3. Screenshot capture

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "screenshot": true,
    "output_format": "json"
  }'
```

### API Endpoints

#### POST /scrape

Main scraping endpoint.

**Request Body:**

```json
{
  "url": "https://example.com",
  "mode": "auto",
  "actions": [
    {
      "type": "click",
      "selector": "#button",
      "wait_after": 1000
    }
  ],
  "extract": {
    "selector": ".content",
    "attribute": null,
    "multiple": false,
    "wait_timeout": 5000,
    "inner_html": false
  },
  "screenshot": false,
  "output_format": "json"
}
```

**Parameters:**

- `url` (string, required): URL to scrape
- `mode` (string, default: "auto"): Scraping mode
  - `auto` - Intelligently choose based on content
  - `static` - Use HTTP requests and HTML parsing (faster, lighter)
  - `dynamic` - Use browser automation (handles JavaScript)
- `actions` (array, optional): List of user actions to perform
- `extract` (object, optional): Content extraction configuration
- `screenshot` (boolean, default: false): Capture screenshot
- `output_format` (string, default: "json"): Response format
  - `json` - Structured data
  - `html` - Raw HTML
  - `text` - Plain text
  - `markdown` - Markdown formatted

**Actions:**

- `click`: Click on element

  - `selector` (string): CSS selector
  - `wait_after` (integer): Wait time after click (ms)

- `type`: Type text into input field

  - `selector` (string): CSS selector
  - `value` (string): Text to type
  - `wait_after` (integer): Wait time after typing (ms)

- `wait`: Wait for condition

  - `condition` (string): One of `selector`, `timeout`, `networkidle`, `load`
  - `value` (string): For selector condition, the CSS selector
  - `timeout` (integer): Timeout in milliseconds

- `scroll`: Scroll to element or by amount
  - `selector` (string, optional): CSS selector to scroll to
  - `amount` (integer, optional): Pixels to scroll

**Extraction Configuration:**

When using `extract`, you can configure:
- `selector` (string, required): CSS selector for element to extract
- `attribute` (string, optional): HTML attribute to extract (e.g., `href`, `src`). If `null`, extracts text content or full HTML
- `multiple` (boolean, default: false): Extract all matching elements
- `wait_timeout` (integer, default: 5000ms): **In dynamic mode only**, wait up to this many milliseconds for the selector to appear. Useful when elements are created dynamically by JavaScript
- `inner_html` (boolean, default: false): If true, return only element contents without the tag wrapper
- `strip` (boolean, default: false): **HTML output only**. If true, removes all HTML attributes (class, id, style, onclick, etc.), scripts, and styles. Keeps only tag structure and text content

**Example with dynamic element waiting:**
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "mode": "dynamic",
    "actions": [
      {"type": "type", "selector": "input[name=\"q\"]", "value": "search term"},
      {"type": "click", "selector": "button[type=\"submit\"]"}
    ],
    "extract": {
      "selector": ".results-table",
      "wait_timeout": 10000,
      "inner_html": false
    }
  }'
```

**Example with HTML stripping:**
```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "output_format": "html",
    "extract": {
      "selector": ".content",
      "strip": true
    }
  }'
```

This returns clean HTML with no attributes, scripts, or styles - just the tag structure and text content.

**Table Parsing:**

Extract table data directly into JSON format by adding `parse_table` configuration to your extraction:

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "extract": {
      "selector": ".data-table",
      "strip": true,
      "parse_table": {
        "headers_selector": "thead th",
        "row_selector": "tbody tr",
        "cell_selector": "td"
      }
    }
  }'
```

**Table Parsing Configuration:**

- `headers_selector` (string, default: "thead th"): CSS selector for header cells
- `row_selector` (string, default: "tbody tr"): CSS selector for data rows
- `cell_selector` (string, default: "td"): CSS selector for cells within rows
- `header_row_index` (integer, optional): If headers are in `tbody` instead of `thead`, specify the row index (0-based). Use `null` to use `headers_selector` instead
- `skip_rows` (array, optional): Row indices to skip (0-based)

**Table Parsing Features:**

- Handles merged cells (`colspan` and `rowspan`)
- Extracts content from nested tables within cells
- Supports multiple `tbody` sections
- Flexible header/row/cell selectors for non-standard table structures

**Response with parsed table:**

```json
{
  "success": true,
  "data": {
    "content": "<table>...</table>",
    "parsed": [
      {"Name": "John", "Age": "30", "City": "New York"},
      {"Name": "Jane", "Age": "25", "City": "Los Angeles"}
    ],
    "table_metadata": {
      "rows_parsed": 2,
      "columns": 3,
      "has_merged_cells": false,
      "nested_tables_found": 0
    },
    "title": "Page Title",
    "url": "https://example.com"
  },
  "metadata": {
    "scrape_mode": "dynamic",
    "duration_ms": 1500,
    "timestamp": "2025-12-09T10:00:00Z",
    "extracted_elements": 1
  },
  "error": null
}
```

**Example: Table with headers in first data row:**

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "extract": {
      "selector": "table",
      "parse_table": {
        "row_selector": "tr",
        "cell_selector": "td",
        "header_row_index": 0,
        "skip_rows": [0]
      }
    }
  }'
```

**Example: Table with merged cells:**

```bash
curl -X POST "http://localhost:8000/scrape" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "extract": {
      "selector": ".report-table",
      "parse_table": {
        "headers_selector": "thead th",
        "row_selector": "tbody tr",
        "cell_selector": "td"
      }
    }
  }'
```

The API will detect merged cells and include metadata: `has_merged_cells: true`. Cell values are properly filled according to colspan/rowspan rules.

**Response:**

```json
{
  "success": true,
  "data": {
    "content": "<table>...</table>",
    "html": null,
    "title": "Page Title",
    "url": "https://example.com"
  },
  "screenshot": "base64_encoded_image_or_null",
  "metadata": {
    "scrape_mode": "dynamic",
    "duration_ms": 1234,
    "timestamp": "2025-12-09T10:00:00Z",
    "actions_performed": 2,
    "extracted_elements": 1,
    "extraction_debug": {
      "selector_matched": true,
      "elements_found": 1,
      "selector_used": ".results-table"
    }
  },
  "error": null
}
```

**Error Response (when selector doesn't match):**
```json
{
  "success": false,
  "data": null,
  "screenshot": null,
  "metadata": {
    "scrape_mode": "dynamic",
    "duration_ms": 1234,
    "timestamp": "2025-12-09T10:00:00Z",
    "actions_performed": 2,
    "extracted_elements": 0,
    "extraction_debug": {
      "selector_matched": false,
      "elements_found": 0,
      "selector_used": ".results-table"
    }
  },
  "error": "Extraction failed: selector '.results-table' matched 0 elements. Possible issues: (1) Element hasn't appeared - try adding a wait action, (2) Selector syntax is incorrect, (3) Element structure changed"
}
```

**Notes on response:**
- When an extraction selector is provided, `data.html` is set to `null` to reduce response size (use `data.content` for extracted HTML)
- `metadata.extraction_debug` shows selector matching information and helps debug extraction issues
- If the selector doesn't match any elements, `success` is `false` and `error` contains helpful suggestions
- In dynamic mode, the scraper automatically waits for your selector to appear (configurable via `wait_timeout`)

#### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "version": "0.1.0",
  "scrapers": {
    "static": "available",
    "dynamic": "available"
  }
}
```

#### GET /

Root endpoint with API information.

## Configuration

Edit `src/config.py` to customize:

- **Timeouts**: HTTP and browser timeouts
- **User Agent**: Custom User-Agent strings
- **Browser settings**: Playwright launch arguments
- **Feature toggles**: Enable/disable static or dynamic scraping
- **Security**: URL validation rules

Key settings:

```python
# HTTP timeouts (seconds)
HTTP_TIMEOUT = 30.0

# Playwright timeout (milliseconds)
PLAYWRIGHT_TIMEOUT = 30000

# Feature toggles
ENABLE_SCREENSHOTS = True
ENABLE_STATIC_MODE = True
ENABLE_DYNAMIC_MODE = True
```

## Development

### Project Structure

```
src/
   main.py                 # FastAPI application
   config.py              # Configuration
   api/
      routes.py          # API endpoints
   models/
      schemas.py         # Pydantic models
   scrapers/
      base.py            # Base scraper interface
      static.py          # Static scraper (httpx + BeautifulSoup)
      dynamic.py         # Dynamic scraper (Playwright)
   services/
       scraper_service.py # Scraper orchestration

tests/
   test_api.py           # API tests
```

### Running Tests

```bash
pytest tests/ -v
```

### Type Checking

```bash
mypy src/
```

## Architecture

### Scraper Modes

**Static Mode** (`StaticScraper`):

- Uses httpx for HTTP requests
- BeautifulSoup for HTML parsing
- Fast, lightweight, low resource usage
- Best for: Static content, simple pages, high-volume scraping

**Dynamic Mode** (`DynamicScraper`):

- Uses Playwright for browser automation
- Handles JavaScript execution
- Supports user interactions and complex scenarios
- Best for: JavaScript-heavy sites, interactive elements, modern web apps

### Service Orchestration

`ScraperService` handles:

- Mode selection (auto, static, or dynamic)
- Request validation
- Error handling and recovery
- Resource cleanup

## Error Handling

The API returns detailed error information:

```json
{
  "success": false,
  "data": null,
  "screenshot": null,
  "metadata": {
    "scrape_mode": "dynamic",
    "duration_ms": 500,
    "timestamp": "2025-12-09T10:00:00Z"
  },
  "error": "Timeout waiting for element '.results' to appear"
}
```

Common errors:

- Invalid URL or scheme
- Element not found
- Timeout waiting for condition
- Network errors
- Browser crashes

## Security Considerations

- **URL validation**: Only HTTP/HTTPS schemes allowed
- **Timeout protection**: All operations have timeouts
- **Resource limits**: Browser pool size configurable
- **Sandboxing**: Playwright runs in headless sandbox mode
- **Input validation**: Pydantic validates all inputs

## Performance Tips

1. **Use static mode** for simple scraping tasks
2. **Set appropriate timeouts** to avoid hanging
3. **Use specific selectors** for faster extraction
4. **Limit action chains** in dynamic mode
5. **Enable caching** in your client application
6. **Batch requests** when possible

## Troubleshooting

### Playwright browser issues

```bash
# Reinstall browsers
playwright install chromium --with-deps
```

### Port already in use

```bash
# Use different port
python -m uvicorn src.main:app --port 8001
```

### Timeout issues

- Increase timeouts in `src/config.py`
- Ensure network connectivity
- Check if website is responding

### "Element not found" errors

- Verify CSS selector is correct
- Check if element loads dynamically
- Increase wait timeout
- Try using dynamic mode instead of static

## License

MIT

## Contributing

Contributions are welcome! Please ensure:

- Code follows PEP 8 style guide
- All tests pass
- Type hints are complete
- Docstrings are present
