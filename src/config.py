"""Configuration settings for the web scraping API."""

from typing import Optional


class Settings:
    """Application settings."""

    # API settings
    API_TITLE = "Web Scraping API"
    API_VERSION = "0.1.0"
    DEBUG = False

    # HTTP Client settings
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    )
    HTTP_TIMEOUT = 30.0
    HTTP_CONNECT_TIMEOUT = 10.0

    # Playwright settings
    PLAYWRIGHT_TIMEOUT = 30000  # milliseconds
    PLAYWRIGHT_LAUNCH_ARGS = {
        "headless": True,
        "args": ["--no-sandbox", "--disable-setuid-sandbox"],
    }
    BROWSER_POOL_SIZE = 1

    # Scraping settings
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    EXTRACTION_TIMEOUT = 60  # seconds

    # Security settings
    MAX_URL_LENGTH = 2048
    ALLOWED_SCHEMES = {"http", "https"}

    # Features
    ENABLE_SCREENSHOTS = True
    ENABLE_STATIC_MODE = True
    ENABLE_DYNAMIC_MODE = True


settings = Settings()
