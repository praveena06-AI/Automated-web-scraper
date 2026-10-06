"""
HTTP Scraping Engine for the Automated Web Scraping Pipeline.

Provides robust web request capabilities including:
- Custom user-agent headers.
- Request timeout management.
- Configurable rate limiting between consecutive calls.
- Automated retry mechanism with exponential backoff for transient network errors.
- Graceful error handling and raw snapshot archiving.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class ScraperError(Exception):
    """Base exception for web scraper errors."""
    pass


class NetworkError(ScraperError):
    """Raised when network-level failures occur (e.g. connection refused, DNS error)."""
    pass


class RequestTimeoutError(ScraperError):
    """Raised when an HTTP request times out."""
    pass


class HTTPStatusError(ScraperError):
    """Raised when the server returns an error status code (4xx, 5xx)."""
    def __init__(self, message: str, status_code: int):
        super().__init__(message)
        self.status_code = status_code


class WebScraper:
    """
    Robust HTTP scraper that adheres to ethical web scraping best practices.

    Attributes:
        user_agent: Custom User-Agent string identifying the crawler politely.
        timeout: Maximum seconds to wait for a network response.
        rate_limit_delay: Minimum seconds to wait between successive requests.
        max_retries: Maximum number of retry attempts for transient server errors.
        raw_data_dir: Optional directory path to archive raw HTML snapshots.
    """

    DEFAULT_USER_AGENT = (
        "TechNewsScraper/1.0 (+https://github.com/internship/automated-web-scraper; "
        "Educational Internship Project; Contact: bot@internship.local)"
    )

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: int = 15,
        rate_limit_delay: float = 1.5,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        raw_data_dir: Optional[Path | str] = None,
    ):
        self.user_agent = user_agent or self.DEFAULT_USER_AGENT
        self.timeout = timeout
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.raw_data_dir = Path(raw_data_dir) if raw_data_dir else None

        self._last_request_time: float = 0.0
        self.session = self._create_session()

        if self.raw_data_dir:
            self.raw_data_dir.mkdir(parents=True, exist_ok=True)

    def _create_session(self) -> requests.Session:
        """Create and configure a requests Session with retries and default headers."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=self.backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
            raise_on_status=False,
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)

        session.headers.update({
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        })

        return session

    def _apply_rate_limiting(self) -> None:
        """Enforce rate limiting between successive HTTP requests."""
        if self._last_request_time > 0:
            elapsed = time.monotonic() - self._last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_duration = self.rate_limit_delay - elapsed
                logger.debug("Rate limiting: sleeping for %.2f seconds", sleep_duration)
                time.sleep(sleep_duration)

    def fetch_page(self, url: str, page_number: Optional[int] = None) -> str:
        """
        Fetch HTML content from a given URL with error handling and rate limiting.

        Args:
            url: The absolute target URL to scrape.
            page_number: Optional page index used for naming raw archives.

        Returns:
            The decoded HTML response string.

        Raises:
            NetworkError: On connection/DNS failure.
            RequestTimeoutError: On request timeout.
            HTTPStatusError: On 4xx/5xx HTTP status codes.
            ScraperError: For other unexpected request issues.
        """
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL provided: '{url}'")

        self._apply_rate_limiting()

        try:
            logger.info("Fetching URL: %s", url)
            response = self.session.get(url, timeout=self.timeout)
            self._last_request_time = time.monotonic()

            if response.status_code != 200:
                logger.error("HTTP error %s for URL: %s", response.status_code, url)
                raise HTTPStatusError(
                    f"Server returned HTTP {response.status_code} for {url}",
                    status_code=response.status_code,
                )

            html_content = response.text
            if not html_content or not html_content.strip():
                raise ScraperError(f"Received empty response body from {url}")

            # Optionally persist raw HTML for auditability and reproducibility
            if self.raw_data_dir:
                self._save_raw_html(html_content, page_number or 1)

            return html_content

        except requests.exceptions.Timeout as exc:
            logger.error("Request timed out while connecting to %s: %s", url, exc)
            raise RequestTimeoutError(f"Connection to {url} timed out after {self.timeout}s") from exc

        except requests.exceptions.ConnectionError as exc:
            logger.error("Network connection error connecting to %s: %s", url, exc)
            raise NetworkError(f"Failed to connect to {url}: {exc}") from exc

        except requests.exceptions.RequestException as exc:
            logger.error("HTTP request error for %s: %s", url, exc)
            raise ScraperError(f"HTTP request failed for {url}: {exc}") from exc

    def _save_raw_html(self, content: str, page_number: int) -> Path:
        """Save a raw HTML snapshot to the raw data directory."""
        filename = f"raw_page_{page_number}.html"
        file_path = self.raw_data_dir / filename
        try:
            file_path.write_text(content, encoding="utf-8")
            logger.debug("Raw HTML saved to %s", file_path)
            return file_path
        except OSError as exc:
            logger.warning("Could not save raw HTML to %s: %s", file_path, exc)
            return file_path

    def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.session:
            self.session.close()

    def __enter__(self) -> "WebScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
