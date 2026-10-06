"""
Main CLI Execution Script for Automated Web Scraping & Data Extraction Pipeline.

Orchestrates the entire ETL workflow:
1. Initialize scraper with rate limiting and retry policies.
2. Extract HTML from target technology news website.
3. Parse structured article items using BeautifulSoup.
4. Transform and clean records with pandas (deduplication, normalization).
5. Load structured data to CSV (data/processed/tech_news.csv) and JSON (data/processed/tech_news.json).
6. Generate analytical summary report (reports/summary.txt).
7. Display concise execution summary to the console.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path
from typing import List, Optional

# Anchor paths relative to this script's directory for robust cross-environment execution
PROJECT_ROOT = Path(__file__).resolve().parent

# Ensure the project directory is on sys.path for direct script execution
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scraper.scraper import (
    HTTPStatusError,
    NetworkError,
    RequestTimeoutError,
    ScraperError,
    WebScraper,
)
from scraper.parser import NewsParser
from scraper.transformer import DataTransformer
from scraper.report import ReportGenerator


def setup_logging(verbose: bool = False) -> None:
    """Configure logging format and level."""
    log_level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def run_pipeline(
    start_url: str = "https://thehackernews.com/",
    max_pages: int = 2,
    rate_limit_delay: float = 1.5,
    timeout: int = 15,
    base_dir: Optional[Path] = None,
    verbose: bool = False,
) -> int:
    """
    Execute the full ETL scraping pipeline.

    Args:
        start_url: Entry point URL for scraping.
        max_pages: Number of sequential pages to scrape via pagination.
        rate_limit_delay: Delay in seconds between HTTP requests.
        timeout: HTTP request timeout in seconds.
        base_dir: Root directory for output data and reports.
        verbose: If True, enables debug level logging.

    Returns:
        Exit code: 0 on success, 1 on handled error.
    """
    root_dir = base_dir or PROJECT_ROOT
    raw_dir = root_dir / "data" / "raw"
    processed_dir = root_dir / "data" / "processed"
    reports_dir = root_dir / "reports"

    csv_path = processed_dir / "tech_news.csv"
    json_path = processed_dir / "tech_news.json"
    report_path = reports_dir / "summary.txt"

    # Display initial banner
    print("=" * 40)
    print("AUTOMATED TECH NEWS SCRAPER")
    print("=" * 40)
    print()
    print("Starting scraper...")

    start_time = time.monotonic()
    all_raw_articles: List[dict] = []
    current_url: Optional[str] = start_url
    pages_scraped = 0

    # Initialize components
    try:
        scraper = WebScraper(
            timeout=timeout,
            rate_limit_delay=rate_limit_delay,
            raw_data_dir=raw_dir,
        )
        parser = NewsParser(
            source_name="The Hacker News",
            base_url=start_url,
        )
        transformer = DataTransformer(default_source="The Hacker News")
        reporter = ReportGenerator(target_source=f"The Hacker News ({start_url})")

        # -------------------------------------------------------------
        # STAGE 1: EXTRACT & PARSE
        # -------------------------------------------------------------
        with scraper:
            while current_url and pages_scraped < max_pages:
                pages_scraped += 1
                try:
                    html_content = scraper.fetch_page(current_url, page_number=pages_scraped)
                except RequestTimeoutError as exc:
                    print(f"\n[Error] Request timeout: {exc}")
                    print("The remote server took too long to respond. Aborting scraper.")
                    return 1
                except NetworkError as exc:
                    print(f"\n[Error] Network failure: {exc}")
                    print("Please check your internet connection or URL accessibility.")
                    return 1
                except HTTPStatusError as exc:
                    print(f"\n[Error] HTTP Error {exc.status_code}: {exc}")
                    return 1
                except ScraperError as exc:
                    print(f"\n[Error] Scraping failure: {exc}")
                    return 1

                # Parse articles from page
                articles = parser.parse_articles(html_content)
                all_raw_articles.extend(articles)

                # Find next page link if more pages requested
                if pages_scraped < max_pages:
                    next_url = parser.extract_next_page_url(html_content)
                    if not next_url:
                        logging.getLogger(__name__).info("No further pagination links found. Stopping.")
                        break
                    current_url = next_url

        print("Request successful.")

        # Guard against completely empty datasets
        if not all_raw_articles:
            print("\n[Warning] No articles could be extracted from the target website.")
            print("The HTML structure may have changed or the page returned no content.")
            return 1

        # -------------------------------------------------------------
        # STAGE 2: TRANSFORM & CLEAN
        # -------------------------------------------------------------
        cleaned_df, transform_stats = transformer.transform(all_raw_articles)

        if cleaned_df.empty:
            print("\n[Warning] All extracted articles were invalid or filtered during cleaning.")
            return 1

        articles_extracted = transform_stats.get("total_raw", len(all_raw_articles))
        duplicates_removed = transform_stats.get("duplicates_removed", 0)

        print(f"Articles extracted: {articles_extracted}")
        print(f"Duplicates removed: {duplicates_removed}")
        print()

        # -------------------------------------------------------------
        # STAGE 3: LOAD (CSV & JSON)
        # -------------------------------------------------------------
        try:
            transformer.save_to_csv(cleaned_df, csv_path)
            # Display relative path for clean terminal output
            rel_csv = csv_path.relative_to(root_dir) if csv_path.is_relative_to(root_dir) else csv_path
            print("CSV saved:")
            print(str(rel_csv).replace("\\", "/"))
            print()

            transformer.save_to_json(cleaned_df, json_path)
            rel_json = json_path.relative_to(root_dir) if json_path.is_relative_to(root_dir) else json_path
            print("JSON saved:")
            print(str(rel_json).replace("\\", "/"))
            print()
        except OSError as exc:
            print(f"\n[Error] File writing error: {exc}")
            return 1

        # -------------------------------------------------------------
        # STAGE 4: ANALYTICAL REPORT
        # -------------------------------------------------------------
        total_duration = time.monotonic() - start_time
        report_text = reporter.generate_report(
            df=cleaned_df,
            transform_stats=transform_stats,
            execution_time_seconds=total_duration,
        )

        try:
            reporter.save_report(report_text, report_path)
            rel_report = report_path.relative_to(root_dir) if report_path.is_relative_to(root_dir) else report_path
            print("Summary report saved:")
            print(str(rel_report).replace("\\", "/"))
            print()
        except OSError as exc:
            print(f"\n[Error] Report file writing error: {exc}")
            return 1

        print("Scraping completed successfully.")
        return 0

    except KeyboardInterrupt:
        print("\n[Interrupted] Scraping aborted by user.")
        return 1
    except Exception as exc:
        print(f"\n[Unexpected Error] An unexpected error occurred: {exc}")
        if verbose:
            import traceback
            traceback.print_exc()
        return 1


def main() -> None:
    """Parse CLI arguments and run pipeline."""
    parser = argparse.ArgumentParser(
        description="Automated Web Scraping & Data Extraction Pipeline for Tech News",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--url",
        type=str,
        default="https://thehackernews.com/",
        help="Initial URL to scrape",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=2,
        help="Maximum number of consecutive pages to scrape",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.5,
        help="Rate limiting delay in seconds between requests",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=15,
        help="HTTP request timeout in seconds",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )

    args = parser.parse_args()
    setup_logging(verbose=args.verbose)

    exit_code = run_pipeline(
        start_url=args.url,
        max_pages=args.pages,
        rate_limit_delay=args.delay,
        timeout=args.timeout,
        verbose=args.verbose,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
