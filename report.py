"""
Analytical Reporting Engine for Scraped Technology News.

Generates comprehensive summary reports detailing:
- Total articles scraped and ingestion metrics
- Unique articles count and duplicate records removed
- Category distribution and frequency breakdown
- Publication date distribution
- Missing values and data integrity analysis
- Top extracted headlines and descriptive statistics
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

logger = logging.getLogger(__name__)


class ReportGenerator:
    """
    Generates and saves analytical text reports summarizing the ETL run.
    """

    def __init__(self, target_source: str = "The Hacker News (https://thehackernews.com)"):
        self.target_source = target_source

    def generate_report(
        self,
        df: pd.DataFrame,
        transform_stats: Dict[str, Any],
        execution_time_seconds: Optional[float] = None,
    ) -> str:
        """
        Generate a structured, human-readable analytical summary report.

        Args:
            df: Cleaned pandas DataFrame of scraped articles.
            transform_stats: Dictionary containing pipeline metrics.
            execution_time_seconds: Optional pipeline duration in seconds.

        Returns:
            Formatted plain-text report string.
        """
        timestamp_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        total_raw = transform_stats.get("total_raw", 0)
        duplicates_removed = transform_stats.get("duplicates_removed", 0)
        invalid_urls_removed = transform_stats.get("invalid_urls_removed", 0)
        missing_titles_removed = transform_stats.get("missing_titles_removed", 0)
        total_clean = len(df)
        unique_urls = df["url"].nunique() if not df.empty and "url" in df.columns else 0

        lines: List[str] = [
            "=" * 78,
            "               AUTOMATED TECH NEWS SCRAPER - SUMMARY REPORT               ",
            "=" * 78,
            f"Generated At      : {timestamp_str}",
            f"Target Source     : {self.target_source}",
            f"Pipeline Duration : {execution_time_seconds:.2f}s" if execution_time_seconds is not None else "Pipeline Duration : N/A",
            "",
            "-" * 78,
            "1. INGESTION & PIPELINE METRICS",
            "-" * 78,
            f"Total Raw Articles Extracted  : {total_raw}",
            f"Duplicate Records Removed     : {duplicates_removed}",
            f"Invalid URLs Removed          : {invalid_urls_removed}",
            f"Missing Title Records Removed : {missing_titles_removed}",
            f"Total Unique Clean Articles   : {total_clean}",
            f"Unique URLs Confirmed         : {unique_urls}",
            "",
            "-" * 78,
            "2. CATEGORY BREAKDOWN",
            "-" * 78,
        ]

        if not df.empty and "category" in df.columns:
            cat_counts = df["category"].fillna("Uncategorized").value_counts()
            if not cat_counts.empty:
                for cat, count in cat_counts.items():
                    pct = (count / total_clean) * 100 if total_clean else 0
                    lines.append(f"  * {cat:<40} : {count:>3} articles ({pct:>5.1f}%)")
            else:
                lines.append("  No category data available.")
        else:
            lines.append("  No category data available.")

        lines.extend([
            "",
            "-" * 78,
            "3. PUBLICATION DATE BREAKDOWN",
            "-" * 78,
        ])

        if not df.empty and "published_date" in df.columns:
            date_counts = df["published_date"].fillna("Date Unavailable").value_counts()
            if not date_counts.empty:
                for date_val, count in date_counts.items():
                    pct = (count / total_clean) * 100 if total_clean else 0
                    lines.append(f"  * {date_val:<40} : {count:>3} articles ({pct:>5.1f}%)")
            else:
                lines.append("  No publication date data available.")
        else:
            lines.append("  No publication date data available.")

        lines.extend([
            "",
            "-" * 78,
            "4. DATA INTEGRITY & MISSING VALUES",
            "-" * 78,
        ])

        missing_vals = transform_stats.get("missing_values", {})
        if not missing_vals and not df.empty:
            missing_vals = {col: int(df[col].isna().sum()) for col in df.columns}

        if missing_vals:
            for col, count in missing_vals.items():
                pct = (count / total_clean) * 100 if total_clean else 0
                lines.append(f"  * {col:<20} : {count:>3} missing ({pct:>5.1f}%)")
        else:
            lines.append("  All fields complete (0 missing values).")

        lines.extend([
            "",
            "-" * 78,
            "5. SAMPLE EXTRACTED HEADLINES & INSIGHTS",
            "-" * 78,
        ])

        if not df.empty:
            avg_title_len = df["title"].str.len().mean() if "title" in df.columns else 0
            lines.append(f"Average Title Length: {avg_title_len:.1f} characters")
            lines.append("")
            lines.append("Top Recent Articles:")

            sample_articles = df.head(5)
            for idx, row in sample_articles.iterrows():
                title = row.get("title", "Untitled")
                cat = row.get("category", "General")
                dt = row.get("published_date", "N/A")
                url = row.get("url", "")
                lines.append(f"  [{idx + 1}] {title}")
                lines.append(f"      Category : {cat} | Date: {dt}")
                lines.append(f"      URL      : {url}")
        else:
            lines.append("  No articles available to display.")

        lines.extend([
            "",
            "=" * 78,
            "END OF SUMMARY REPORT",
            "=" * 78,
        ])

        return "\n".join(lines) + "\n"

    def save_report(self, report_text: str, filepath: Union[str, Path]) -> Path:
        """
        Save the generated report to a text file.

        Args:
            report_text: Formatted report content.
            filepath: Destination file path.

        Returns:
            Resolved Path of the saved report.

        Raises:
            IOError: If writing to the file fails.
        """
        path = Path(filepath).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(report_text, encoding="utf-8")
            logger.info("Saved summary report to %s", path)
            return path
        except OSError as exc:
            logger.error("Failed to write report file to %s: %s", path, exc)
            raise IOError(f"Could not save report to {path}: {exc}") from exc
