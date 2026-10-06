"""
HTML Parsing Module for Technology News Articles.

Uses BeautifulSoup to parse raw HTML and extract structured article records:
- Article title
- Article URL
- Publication date (if available)
- Category / Tag (if available)
- Author (if available)
- Source website name
- Summary snippet (if available)
- Next page link for pagination
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class NewsParser:
    """
    Parses technology news HTML content into structured dictionary records.

    Attributes:
        source_name: Human-readable name of the source publication.
        base_url: Base URL used for resolving relative hyperlinks.
    """

    def __init__(
        self,
        source_name: str = "The Hacker News",
        base_url: str = "https://thehackernews.com/",
    ):
        self.source_name = source_name
        self.base_url = base_url

    def parse_articles(self, html_content: str) -> List[Dict[str, Any]]:
        """
        Parse HTML and return a list of extracted raw article dictionaries.

        Args:
            html_content: Raw HTML text of the scraped page.

        Returns:
            List of dictionaries containing raw article fields.
        """
        if not html_content or not isinstance(html_content, str) or not html_content.strip():
            logger.warning("Empty or non-string HTML passed to parse_articles.")
            return []

        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception as exc:
            logger.error("Failed to parse HTML with BeautifulSoup: %s", exc)
            return []

        articles: List[Dict[str, Any]] = []

        # Find primary story containers (The Hacker News standard: div.body-post)
        containers = soup.find_all("div", class_=lambda c: c and "body-post" in c.split())

        # Fallback 1: check for story-link wrappers if body-post is not found
        if not containers:
            containers = soup.find_all("a", class_=lambda c: c and "story-link" in c.split())

        # Fallback 2: check for generic article tags or story cards
        if not containers:
            containers = soup.find_all(["article", "li"], class_=re.compile(r"story|post|article", re.I))

        logger.debug("Found %d candidate story containers on page.", len(containers))

        for container in containers:
            try:
                article_data = self._extract_article(container)
                if article_data:
                    articles.append(article_data)
            except Exception as exc:
                logger.warning("Error extracting article from container: %s", exc)
                continue

        logger.info("Successfully parsed %d articles from page.", len(articles))
        return articles

    def _extract_article(self, container: Any) -> Optional[Dict[str, Any]]:
        """
        Extract structured fields from a single story container element.

        Args:
            container: BeautifulSoup Tag representing an article card.

        Returns:
            Dictionary with article fields or None if essential fields are absent.
        """
        # --- 1. Article Link & Title ---
        link_elem = None
        if container.name == "a" and container.get("href"):
            link_elem = container
        else:
            link_elem = container.find("a", class_=lambda c: c and "story-link" in c.split()) or container.find("a", href=True)

        if not link_elem:
            return None

        raw_url = link_elem.get("href", "").strip()
        if not raw_url:
            return None

        # Resolve relative URLs against base_url
        article_url = urljoin(self.base_url, raw_url)

        # Title: usually inside h2.home-title or h2, h3, or link text
        title_elem = container.find(["h2", "h3"], class_=lambda c: c and "home-title" in c.split())
        if not title_elem:
            title_elem = container.find(["h2", "h3", "h1"])

        if title_elem:
            title = title_elem.get_text(strip=True)
        else:
            title = link_elem.get_text(strip=True)

        # If title is still missing or just whitespace, skip
        if not title:
            return None

        # --- 2. Publication Date ---
        published_date = None
        date_elem = container.find("span", class_=lambda c: c and "h-datetime" in c.split())
        if not date_elem:
            date_elem = container.find(["time", "span"], class_=re.compile(r"date|time", re.I))

        if date_elem:
            # Clone and remove any icon elements inside the date tag
            # e.g., <i class="icon-font icon-calendar"></i>
            date_text = "".join(
                c for c in date_elem.contents
                if getattr(c, "name", None) not in ["i", "svg", "img"]
            ).strip()
            # If contents extraction produced text, use it; otherwise fallback to get_text
            published_date = date_text or date_elem.get_text(strip=True)
            # Remove any leading/trailing unicode symbols (e.g. \ue802)
            published_date = re.sub(r"[^\x20-\x7E]+", "", published_date).strip()
            if not published_date:
                published_date = None

        # --- 3. Category / Tag ---
        category = None
        tag_elem = container.find("span", class_=lambda c: c and "h-tags" in c.split())
        if not tag_elem:
            tag_elem = container.find(["span", "a"], class_=re.compile(r"tag|category|label", re.I))

        if tag_elem:
            raw_category = tag_elem.get_text(strip=True)
            raw_category = re.sub(r"[^\x20-\x7E/ ]+", "", raw_category).strip()
            if raw_category:
                category = raw_category

        # --- 4. Author ---
        author = None
        author_elem = container.find(["span", "a"], class_=lambda c: c and any(k in str(c).lower() for k in ["author", "byline", "u-author"]))
        if author_elem:
            raw_author = author_elem.get_text(strip=True)
            # Strip "By " prefix if present
            raw_author = re.sub(r"^by\s+", "", raw_author, flags=re.I).strip()
            if raw_author:
                author = raw_author

        # --- 5. Summary Snippet ---
        summary = None
        desc_elem = container.find("div", class_=lambda c: c and "home-desc" in c.split())
        if not desc_elem:
            desc_elem = container.find(["p", "div"], class_=re.compile(r"desc|snippet|summary", re.I))

        if desc_elem:
            summary_text = desc_elem.get_text(separator=" ", strip=True)
            # Clean up whitespace
            summary_text = re.sub(r"\s+", " ", summary_text).strip()
            if summary_text:
                summary = summary_text

        return {
            "title": title,
            "url": article_url,
            "published_date": published_date,
            "category": category,
            "author": author,
            "summary": summary,
            "source_website": self.source_name,
        }

    def extract_next_page_url(self, html_content: str) -> Optional[str]:
        """
        Extract the URL for the next page of articles to support pagination.

        Args:
            html_content: Raw HTML text of the scraped page.

        Returns:
            Absolute URL for the next page, or None if no further pages exist.
        """
        if not html_content or not isinstance(html_content, str):
            return None

        try:
            soup = BeautifulSoup(html_content, "html.parser")
        except Exception:
            return None

        # Look for The Hacker News pagination link
        # <a class="blog-pager-older-link-mobile" href="...">Next Page</a>
        pager_link = (
            soup.find("a", class_=lambda c: c and "blog-pager-older-link" in str(c))
            or soup.find("a", string=re.compile(r"next page|older posts|older", re.I))
            or soup.find("a", id=re.compile(r"load_more|older", re.I))
        )

        if pager_link and pager_link.get("href"):
            raw_href = pager_link["href"].strip()
            if raw_href and not raw_href.startswith(("#", "javascript:")):
                return urljoin(self.base_url, raw_href)

        return None
