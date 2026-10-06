"""
Unit tests for the NewsParser component.

Verifies:
- Extraction of structured article fields from HTML.
- Handling of missing, malformed, or empty HTML content.
- Graceful handling of missing optional metadata (dates, categories, authors).
- Next-page pagination link extraction.
All tests use offline mocked HTML fixtures without network requests.
"""

import pytest
from scraper.parser import NewsParser

# Realistic sample HTML fixture mirroring The Hacker News layout
SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head><title>The Hacker News</title></head>
<body>
  <div class="blog-posts">
    <!-- Article 1: Complete with all fields -->
    <div class="body-post clear">
      <a class="story-link" href="https://thehackernews.com/2026/09/sample-article-1.html">
        <div class="home-post-box">
          <div class="home-right">
            <h2 class="home-title">Critical Zero-Day Vulnerability Discovered in Core Cloud Services</h2>
            <div class="item-label">
              <span class="h-datetime"><i class="icon-font icon-calendar"></i>Sep 25, 2026</span>
              <span class="h-tags">Cloud Security / Vulnerability</span>
            </div>
            <div class="home-desc">
              Security researchers have disclosed a critical remote code execution vulnerability impacting cloud clusters worldwide.
            </div>
          </div>
        </div>
      </a>
    </div>

    <!-- Article 2: Relative URL and different category -->
    <div class="body-post clear">
      <a class="story-link" href="/2026/09/sample-article-2.html">
        <div class="home-post-box">
          <div class="home-right">
            <h2 class="home-title">New Python Ransomware Campaign Targets Developer Repositories</h2>
            <div class="item-label">
              <span class="h-datetime"><i class="icon-font icon-calendar"></i>Sep 24, 2026</span>
              <span class="h-tags">Malware / Ransomware</span>
            </div>
            <div class="home-desc">
              A sophisticated malware strain written in Python is actively harvesting API credentials.
            </div>
          </div>
        </div>
      </a>
    </div>

    <!-- Article 3: Missing date and tags -->
    <div class="body-post clear">
      <a class="story-link" href="https://thehackernews.com/2026/09/sample-article-3.html">
        <div class="home-post-box">
          <div class="home-right">
            <h2 class="home-title">Open Source Security Foundation Announces New Guidelines</h2>
            <div class="home-desc">
              New guidelines provide best practices for securing CI/CD pipelines.
            </div>
          </div>
        </div>
      </a>
    </div>

    <!-- Invalid Card: Missing title and link -->
    <div class="body-post clear">
      <div class="home-post-box">
        <div class="home-right">
          <p>Ad banner or empty container without title or link</p>
        </div>
      </div>
    </div>
  </div>

  <!-- Pagination Link -->
  <div id="blog-pager" class="blog-pager clear">
    <a class="blog-pager-older-link-mobile" href="/search?updated-max=2026-09-24T12:00:00Z&amp;max-results=16">
      Next Page
    </a>
  </div>
</body>
</html>
"""


@pytest.fixture
def parser():
    return NewsParser(
        source_name="The Hacker News",
        base_url="https://thehackernews.com/",
    )


def test_parse_articles_count(parser):
    """Verify that only valid articles are extracted and invalid containers are skipped."""
    articles = parser.parse_articles(SAMPLE_HTML)
    # 3 valid articles, 1 invalid container skipped
    assert len(articles) == 3


def test_parse_articles_field_extraction(parser):
    """Verify accurate extraction of all structured fields from article 1."""
    articles = parser.parse_articles(SAMPLE_HTML)
    art1 = articles[0]

    assert art1["title"] == "Critical Zero-Day Vulnerability Discovered in Core Cloud Services"
    assert art1["url"] == "https://thehackernews.com/2026/09/sample-article-1.html"
    assert art1["published_date"] == "Sep 25, 2026"
    assert art1["category"] == "Cloud Security / Vulnerability"
    assert art1["source_website"] == "The Hacker News"
    assert "critical remote code execution" in art1["summary"]


def test_parse_articles_resolves_relative_url(parser):
    """Verify that relative links are resolved into absolute URLs."""
    articles = parser.parse_articles(SAMPLE_HTML)
    art2 = articles[1]

    assert art2["url"] == "https://thehackernews.com/2026/09/sample-article-2.html"
    assert art2["published_date"] == "Sep 24, 2026"
    assert art2["category"] == "Malware / Ransomware"


def test_parse_articles_handles_missing_optional_fields(parser):
    """Verify that articles with missing dates or tags do not cause crashes."""
    articles = parser.parse_articles(SAMPLE_HTML)
    art3 = articles[2]

    assert art3["title"] == "Open Source Security Foundation Announces New Guidelines"
    assert art3["published_date"] is None
    assert art3["category"] is None
    assert art3["url"] == "https://thehackernews.com/2026/09/sample-article-3.html"


def test_parse_articles_empty_html(parser):
    """Verify that empty or whitespace HTML returns an empty list without error."""
    assert parser.parse_articles("") == []
    assert parser.parse_articles("   ") == []
    assert parser.parse_articles(None) == []


def test_parse_articles_malformed_html(parser):
    """Verify that broken or truncated HTML doesn't crash the parser."""
    malformed = "<div><h2>Incomplete <a href='https://test.com'>Link"
    result = parser.parse_articles(malformed)
    assert isinstance(result, list)


def test_extract_next_page_url_success(parser):
    """Verify extraction and resolution of pagination next page URL."""
    next_url = parser.extract_next_page_url(SAMPLE_HTML)
    assert next_url is not None
    assert "https://thehackernews.com/search?updated-max=" in next_url


def test_extract_next_page_url_absent(parser):
    """Verify that None is returned when no pagination link exists."""
    html_without_pager = "<html><body><p>No pager</p></body></html>"
    assert parser.extract_next_page_url(html_without_pager) is None
    assert parser.extract_next_page_url("") is None
