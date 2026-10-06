"""
Unit tests for the DataTransformer and ReportGenerator components.

Verifies:
- Data transformation and normalization.
- Whitespace stripping and non-printable character removal.
- Duplicate detection and removal across URLs and titles.
- Filtering of invalid or malicious URLs.
- Missing field handling and integrity tracking.
- CSV and JSON serialization with round-trip verification.
- Report generation accuracy.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

from scraper.transformer import DataTransformer, EXPECTED_COLUMNS
from scraper.report import ReportGenerator


@pytest.fixture
def transformer():
    return DataTransformer(default_source="The Hacker News")


@pytest.fixture
def sample_records():
    return [
        {
            "title": "  Python 3.14 Released with Enhanced Performance  ",
            "url": "https://thehackernews.com/2026/09/python-release.html",
            "published_date": "Sep 25, 2026",
            "category": "Development / Python",
            "author": "Guido Staff",
            "summary": "  Significant performance upgrades in Python runtime.  ",
            "source_website": "The Hacker News",
        },
        # Duplicate URL of record 1
        {
            "title": "Python 3.14 Released with Enhanced Performance - Duplicate",
            "url": "https://thehackernews.com/2026/09/python-release.html",
            "published_date": "Sep 25, 2026",
            "category": "Development",
            "author": "Another Author",
            "summary": "Duplicate entry.",
            "source_website": "The Hacker News",
        },
        # Duplicate Title with different URL
        {
            "title": "Python 3.14 Released with Enhanced Performance",
            "url": "https://thehackernews.com/2026/09/another-python-url.html",
            "published_date": "Sep 25, 2026",
            "category": "Development",
            "author": "Staff",
            "summary": "Another duplicate.",
            "source_website": "The Hacker News",
        },
        # Invalid URL record
        {
            "title": "Malicious or Bad Link",
            "url": "javascript:alert('xss')",
            "published_date": "Sep 24, 2026",
            "category": "Security",
            "author": "Unknown",
            "summary": "Should be filtered out.",
            "source_website": "The Hacker News",
        },
        # Record missing title
        {
            "title": "   ",
            "url": "https://thehackernews.com/2026/09/no-title.html",
            "published_date": "Sep 24, 2026",
            "category": "Security",
            "author": "Unknown",
            "summary": "No title present.",
            "source_website": "The Hacker News",
        },
        # Valid distinct record with missing category/author
        {
            "title": "Zero-Trust Architecture Guidelines",
            "url": "https://thehackernews.com/2026/09/zero-trust.html",
            "published_date": "Sep 23, 2026",
            "category": None,
            "author": None,
            "summary": "Guidelines for zero-trust deployment.",
            "source_website": None,
        },
    ]


def test_clean_data_whitespace(transformer):
    """Verify leading, trailing, and redundant internal whitespace is cleaned."""
    raw = [{
        "title": "  Too   Many    Spaces   Here  \n",
        "url": "https://example.com/clean-spaces",
        "published_date": "  Sep 25, 2026  ",
        "category": " Tech \t News ",
        "author": " Jane \n Doe ",
        "summary": " Multiple   spaces   in   summary. ",
        "source_website": "The Hacker News",
    }]

    df, _ = transformer.transform(raw)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["title"] == "Too Many Spaces Here"
    assert row["published_date"] == "Sep 25, 2026"
    assert row["category"] == "Tech News"
    assert row["author"] == "Jane Doe"
    assert row["summary"] == "Multiple spaces in summary."


def test_duplicate_removal(transformer, sample_records):
    """Verify that duplicate URLs and titles are removed and properly counted."""
    df, stats = transformer.transform(sample_records)

    # In sample_records:
    # 6 initial records
    # 1 removed for missing title
    # 1 removed for invalid URL (javascript:...)
    # 2 removed as duplicates (1 by URL, 1 by title)
    # 2 clean unique records should remain
    assert stats["total_raw"] == 6
    assert stats["missing_titles_removed"] == 1
    assert stats["invalid_urls_removed"] == 1
    assert stats["duplicates_removed"] == 2
    assert stats["total_clean"] == 2
    assert len(df) == 2


def test_invalid_url_filtering(transformer):
    """Verify filtering of various invalid URL forms."""
    invalid_samples = [
        {"title": "Test 1", "url": "#anchor", "source_website": "Test"},
        {"title": "Test 2", "url": "not-a-url", "source_website": "Test"},
        {"title": "Test 3", "url": "mailto:test@example.com", "source_website": "Test"},
        {"title": "Test 4", "url": "", "source_website": "Test"},
        {"title": "Test 5", "url": None, "source_website": "Test"},
    ]
    df, stats = transformer.transform(invalid_samples)
    assert len(df) == 0
    assert stats["total_clean"] == 0


def test_missing_field_handling(transformer):
    """Verify handling of records with missing optional fields."""
    records = [{
        "title": "Article with Minimal Fields",
        "url": "https://thehackernews.com/article-min.html",
        "published_date": None,
        "category": None,
        "author": None,
        "summary": None,
        "source_website": None,
    }]

    df, stats = transformer.transform(records)
    assert len(df) == 1
    row = df.iloc[0]

    # Category defaults to 'General Tech'
    assert row["category"] == "General Tech"
    # Source website defaults to 'The Hacker News'
    assert row["source_website"] == "The Hacker News"
    # Date and author remain None for accurate missing-value tracking
    assert pd.isna(row["published_date"])
    assert pd.isna(row["author"])
    assert stats["missing_values"]["published_date"] == 1
    assert stats["missing_values"]["author"] == 1


def test_empty_dataset(transformer):
    """Verify that an empty list returns an empty DataFrame and valid stats."""
    df, stats = transformer.transform([])
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0
    assert list(df.columns) == EXPECTED_COLUMNS
    assert stats["total_raw"] == 0
    assert stats["total_clean"] == 0


def test_save_to_csv_and_json(transformer, tmp_path):
    """Verify CSV and JSON file serialization and round-trip readability."""
    data = [{
        "title": "Persistent Article Test",
        "url": "https://thehackernews.com/persistent.html",
        "published_date": "Sep 25, 2026",
        "category": "Cybersecurity",
        "author": "Alice Smith",
        "summary": "This is a test summary for file writing.",
        "source_website": "The Hacker News",
    }]
    df, _ = transformer.transform(data)

    csv_file = tmp_path / "data" / "processed" / "tech_news.csv"
    json_file = tmp_path / "data" / "processed" / "tech_news.json"

    saved_csv = transformer.save_to_csv(df, csv_file)
    saved_json = transformer.save_to_json(df, json_file)

    assert saved_csv.exists()
    assert saved_json.exists()

    # Read back CSV
    read_df = pd.read_csv(saved_csv)
    assert len(read_df) == 1
    assert read_df.iloc[0]["title"] == "Persistent Article Test"

    # Read back JSON
    with open(saved_json, "r", encoding="utf-8") as f:
        read_json = json.load(f)
    assert len(read_json) == 1
    assert read_json[0]["url"] == "https://thehackernews.com/persistent.html"


def test_report_generation(transformer, sample_records):
    """Verify that ReportGenerator produces a formatted text report with required sections."""
    df, stats = transformer.transform(sample_records)
    reporter = ReportGenerator(target_source="Test News Source")

    report_text = reporter.generate_report(df, stats, execution_time_seconds=1.23)

    assert "AUTOMATED TECH NEWS SCRAPER - SUMMARY REPORT" in report_text
    assert "INGESTION & PIPELINE METRICS" in report_text
    assert "CATEGORY BREAKDOWN" in report_text
    assert "PUBLICATION DATE BREAKDOWN" in report_text
    assert "DATA INTEGRITY & MISSING VALUES" in report_text
    assert "Total Raw Articles Extracted  : 6" in report_text
    assert "Duplicate Records Removed     : 2" in report_text
    assert "Total Unique Clean Articles   : 2" in report_text
