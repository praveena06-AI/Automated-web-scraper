"""
Data Transformation & Cleaning Engine for Technology News.

Cleans, validates, deduplicates, and serializes scraped articles into
structured tabular data (CSV) and semi-structured documents (JSON).
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlparse

import pandas as pd

logger = logging.getLogger(__name__)

# Standard schema definition
EXPECTED_COLUMNS = [
    "title",
    "url",
    "published_date",
    "category",
    "author",
    "summary",
    "source_website",
]


class DataTransformer:
    """
    Transforms raw scraped article records into cleaned, structured datasets.

    Handles:
    - Whitespace stripping and internal whitespace normalization.
    - URL validation and malformed link removal.
    - Duplicate detection and removal (based on URL and title).
    - Missing value normalization and tracking.
    - Exporting to CSV and JSON formats with comprehensive error handling.
    """

    def __init__(self, default_source: str = "The Hacker News"):
        self.default_source = default_source

    @staticmethod
    def _is_valid_url(url: Optional[str]) -> bool:
        """Validate whether a string is a well-formed HTTP/HTTPS URL."""
        if not url or not isinstance(url, str):
            return False
        url = url.strip()
        if url.startswith(("javascript:", "#", "mailto:", "tel:")):
            return False
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme in ("http", "https") and parsed.netloc and "." in parsed.netloc)
        except Exception:
            return False

    @staticmethod
    def _clean_text(val: Any) -> Optional[str]:
        """Strip leading/trailing whitespace, collapse internal spaces, and clean artifacts."""
        if val is None or pd.isna(val):
            return None
        text = str(val).strip()
        if not text or text.lower() in ("none", "n/a", "null", "undefined"):
            return None
        # Normalize multiple spaces, tabs, and newlines to a single space
        text = re.sub(r"\s+", " ", text)
        # Remove non-printable / control characters while preserving unicode letters and punctuation
        text = re.sub(r"[\x00-\x1f\x7f-\x9f]", "", text)
        return text.strip() or None

    def transform(self, raw_records: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Clean, normalize, and deduplicate a list of raw article dictionaries.

        Args:
            raw_records: List of raw dictionaries extracted by the parser.

        Returns:
            Tuple of:
                - Cleaned pandas DataFrame adhering to EXPECTED_COLUMNS schema.
                - Transformation statistics dictionary.
        """
        raw_count = len(raw_records) if raw_records else 0

        stats: Dict[str, Any] = {
            "total_raw": raw_count,
            "duplicates_removed": 0,
            "invalid_urls_removed": 0,
            "missing_titles_removed": 0,
            "total_clean": 0,
            "missing_values": {},
        }

        if not raw_records:
            logger.warning("Empty records list provided to transform.")
            df = pd.DataFrame(columns=EXPECTED_COLUMNS)
            stats["missing_values"] = {col: 0 for col in EXPECTED_COLUMNS}
            return df, stats

        # Convert to initial DataFrame
        df = pd.DataFrame(raw_records)

        # Ensure all expected columns exist
        for col in EXPECTED_COLUMNS:
            if col not in df.columns:
                df[col] = None

        # Reorder to consistent schema
        df = df[EXPECTED_COLUMNS].copy()

        # Step 1: Clean all text fields (whitespace, non-printable chars)
        for col in EXPECTED_COLUMNS:
            df[col] = df[col].apply(self._clean_text)

        # Step 2: Ensure source_website has default if missing
        df["source_website"] = df["source_website"].fillna(self.default_source)

        # Step 3: Remove records with missing or empty titles
        initial_len = len(df)
        df = df[df["title"].notna() & (df["title"] != "")]
        missing_titles_count = initial_len - len(df)
        stats["missing_titles_removed"] = missing_titles_count
        if missing_titles_count > 0:
            logger.info("Removed %d records missing article title.", missing_titles_count)

        # Step 4: Validate URLs and remove invalid ones
        pre_url_len = len(df)
        df = df[df["url"].apply(self._is_valid_url)]
        invalid_urls_count = pre_url_len - len(df)
        stats["invalid_urls_removed"] = invalid_urls_count
        if invalid_urls_count > 0:
            logger.info("Removed %d records with invalid URLs.", invalid_urls_count)

        # Step 5: Duplicate Removal
        # Check duplicates primarily by normalized URL, secondarily by title
        pre_dedup_len = len(df)
        # Drop duplicates by URL (keep first occurrence)
        df = df.drop_duplicates(subset=["url"], keep="first")
        # Drop duplicates by title as well
        df = df.drop_duplicates(subset=["title"], keep="first")
        duplicates_removed = pre_dedup_len - len(df)
        stats["duplicates_removed"] = duplicates_removed
        if duplicates_removed > 0:
            logger.info("Removed %d duplicate article records.", duplicates_removed)

        # Step 6: Standardize categorical defaults
        # For category: if None, assign 'Uncategorized' for clear group reporting
        df["category"] = df["category"].fillna("General Tech")
        # For author: if None, assign 'Editorial Staff' or keep None for missing stats
        # Prompt requires: "Number of missing values", so let's keep raw None for author/date if not found
        # but author can default to 'The Hacker News' or None. Let's record missing values accurately.

        # Reset DataFrame index
        df = df.reset_index(drop=True)
        stats["total_clean"] = len(df)

        # Count missing values per column
        stats["missing_values"] = {
            col: int(df[col].isna().sum()) for col in EXPECTED_COLUMNS
        }

        logger.info(
            "Transformation complete. Clean records: %d (Duplicates removed: %d)",
            stats["total_clean"],
            stats["duplicates_removed"],
        )
        return df, stats

    def save_to_csv(self, df: pd.DataFrame, filepath: Union[str, Path]) -> Path:
        """
        Save DataFrame to CSV file with UTF-8 encoding and directory auto-creation.

        Args:
            df: Cleaned pandas DataFrame.
            filepath: Destination file path.

        Returns:
            Resolved Path of the saved CSV.

        Raises:
            IOError: On file system or permission errors.
        """
        path = Path(filepath).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            df.to_csv(path, index=False, encoding="utf-8")
            logger.info("Successfully wrote CSV to %s (%d rows)", path, len(df))
            return path
        except OSError as exc:
            logger.error("Failed to write CSV file to %s: %s", path, exc)
            raise IOError(f"Could not save CSV to {path}: {exc}") from exc

    def save_to_json(self, df: pd.DataFrame, filepath: Union[str, Path]) -> Path:
        """
        Save DataFrame to formatted JSON records file.

        Args:
            df: Cleaned pandas DataFrame.
            filepath: Destination file path.

        Returns:
            Resolved Path of the saved JSON.

        Raises:
            IOError: On file system or permission errors.
        """
        path = Path(filepath).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            records = df.to_dict(orient="records")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(records, f, indent=2, ensure_ascii=False)
            logger.info("Successfully wrote JSON to %s (%d records)", path, len(records))
            return path
        except OSError as exc:
            logger.error("Failed to write JSON file to %s: %s", path, exc)
            raise IOError(f"Could not save JSON to {path}: {exc}") from exc
