# Automated Web Scraping & Data Extraction Pipeline

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code Style: Clean](https://img.shields.io/badge/Code%20Style-PEP%208-brightgreen.svg)](https://pep8.org/)
[![Tests: Pytest](https://img.shields.io/badge/Tests-Passing-success.svg)](tests/)

An enterprise-ready, modular **ETL (Extract, Transform, Load) Web Scraping & Analytical Data Pipeline** developed in Python. This project extracts publicly accessible technology news, parses semantic HTML, cleans and deduplicates the records using `pandas`, exports structured datasets in CSV and JSON formats, and automatically compiles an analytical summary report.

Designed and engineered for a **Python Software Engineering Internship Submission**.

---

## Table of Contents

- [Project Overview](#project-overview)
- [Objective](#objective)
- [Key Features](#key-features)
- [Architecture & ETL Workflow](#architecture--etl-workflow)
- [Technologies Used](#technologies-used)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Running the Scraper](#running-the-scraper)
- [Output Files & Schema](#output-files--schema)
- [Example Execution Output](#example-execution-output)
- [Analytical Reporting](#analytical-reporting)
- [Web Scraping Ethics & Responsible Use](#web-scraping-ethics--responsible-use)
- [Testing & Quality Assurance](#testing--quality-assurance)
- [Error Handling & Reliability](#error-handling--reliability)
- [Author & Internship Details](#author--internship-details)

---

## Project Overview

Modern software applications often rely on automated data pipelines to track industry trends, detect security disclosures, and aggregate technology news from disparate web publications. This application demonstrates an end-to-end, production-grade web scraping solution targeting **The Hacker News** (`https://thehackernews.com`), one of the foremost global cybersecurity and technology news platforms.

The pipeline adheres to strict scraping ethics, respecting target web servers through controlled rate limiting, custom headers, request timeouts, and exponential backoff retry strategies.

---

## Objective

- **Extract**: Systematically retrieve technology news articles across multiple paginated listing pages without tripping server anti-bot protections or violating access rules.
- **Transform**: Clean text, strip artifact characters, validate URL schemas, handle missing values, and deduplicate articles across title and URL dimensions using `pandas`.
- **Load**: Persist cleaned, normalized data into standardized machine-readable formats (`.csv` and `.json`).
- **Analyze**: Compute real-time dataset statistics (category distribution, publication cadence, missing data ratios) and output a clean executive summary report.
- **Assure Quality**: Verify pipeline logic with unit tests using `pytest` without relying on active network calls.

---

## Key Features

- **Modular Architecture**: Clean separation of concerns across extraction (`WebScraper`), parsing (`NewsParser`), transformation (`DataTransformer`), and reporting (`ReportGenerator`).
- **Polite & Ethical Scraping**:
  - Custom informative `User-Agent` header.
  - Per-request configurable rate limiting (default 1.5s).
  - Explicit timeouts (15s) and automated session connection pooling.
  - Exponential backoff retry adapter for transient network failures (HTTP 429, 500, 502, 503, 504).
  - 100% compliance with target `robots.txt`.
- **Intelligent HTML Parsing**:
  - BeautifulSoup-based extraction resilient to minor markup variations.
  - Multi-level fallback selector strategies for titles, links, dates, and categories.
  - Next-page pagination detection and absolute URL resolution via `urllib.parse`.
- **Data Quality & Transformation Engine**:
  - Whitespace cleaning, control character removal, and non-printable symbol filtering.
  - URL format validation (ensures valid `http`/`https` protocols and fully-qualified domains).
  - Multi-attribute deduplication (removes redundant articles sharing URLs or titles).
  - Schema consistency enforcement across 7 standardized data attributes.
- **Dual Export Formats**: Automatically exports to both `data/processed/tech_news.csv` (UTF-8 encoded) and `data/processed/tech_news.json` (formatted JSON records).
- **Automated Summary Statistics**: Generates `reports/summary.txt` with category frequencies, publication dates, data integrity metrics, and headline previews.
- **Robust Exception Handling**: Captures network timeouts, DNS errors, HTTP status issues, and filesystem write failures with clear messages—no uncontrolled stack traces.
- **Unit Test Suite**: Fast, hermetic unit tests using `pytest` and mocked HTML fixtures.

---

## Architecture & ETL Workflow

```text
┌────────────────────────────────────────────────────────┐
│                   TARGET WEBSITE                       │
│              (https://thehackernews.com)               │
└──────────────────────────┬─────────────────────────────┘
                           │
                 [1. EXTRACT] HTTP GET
                           │  - Custom User-Agent
                           │  - Rate Limiting (1.5s delay)
                           │  - Retry / Backoff Strategy
                           ▼
┌────────────────────────────────────────────────────────┐
│                      scraper.py                        │
│                 (WebScraper Engine)                    │
└──────────────────────────┬─────────────────────────────┘
                           │ Raw HTML Response
                           ▼
┌────────────────────────────────────────────────────────┐
│                      parser.py                         │
│               (BeautifulSoup Parser)                   │
└──────────────────────────┬─────────────────────────────┘
                           │ Raw Extracted Dictionaries
                           ▼
┌────────────────────────────────────────────────────────┐
│                   transformer.py                       │
│              (pandas Data Cleaning)                    │
│   - Strip Whitespace & Control Chars                   │
│   - Validate URLs                                      │
│   - Deduplicate Records                                │
│   - Normalize Missing Fields                           │
└──────────────────────────┬─────────────────────────────┘
                           │ Cleaned DataFrame
          ┌────────────────┴────────────────┐
          ▼                                 ▼
   [3. LOAD / EXPORT]              [4. REPORT GENERATION]
  data/processed/tech_news.csv       reports/summary.txt
  data/processed/tech_news.json
```

### Detailed Pipeline Stages

1. **Extract**:
   `WebScraper.fetch_page()` queries the target website with an identifiable `User-Agent`. If pagination is enabled, it follows subsequent page tokens. Raw HTML snapshots can optionally be archived in `data/raw/` for auditing.
2. **Transform**:
   `NewsParser.parse_articles()` utilizes BeautifulSoup to find all article cards (`div.body-post`), resolving relative links into fully-qualified URLs and extracting titles, dates, categories, authors, and summaries.
   `DataTransformer.transform()` takes raw dictionaries into a `pandas.DataFrame`, cleans whitespace, filters malformed links (`javascript:`, `#`), drops records missing critical titles, and deduplicates identical articles.
3. **Load**:
   The sanitized DataFrame is written to `data/processed/tech_news.csv` using UTF-8 encoding and to `data/processed/tech_news.json` with indentation for downstream analytics or consumption by REST APIs.
4. **Report**:
   `ReportGenerator.generate_report()` aggregates high-level KPIs, category proportions, date frequencies, and missing value counts, writing an analytical overview to `reports/summary.txt`.

---

## Technologies Used

| Technology | Purpose |
| :--- | :--- |
| **Python 3.10+** | Core programming language |
| **Requests** | HTTP client with connection pooling, timeouts, and headers |
| **BeautifulSoup4** | HTML parsing, DOM navigation, and attribute extraction |
| **Pandas** | High-performance tabular data cleaning, deduplication, and transformation |
| **Urllib3** | Retry strategy with exponential backoff for HTTP status codes |
| **Pytest** | Testing framework for unit and regression validation |

---

## Project Structure

```text
automated-web-scraper/
├── scraper/
│   ├── __init__.py          # Package exports (WebScraper, NewsParser, DataTransformer, ReportGenerator)
│   ├── scraper.py           # HTTP request engine with retries, rate limiting, and timeouts
│   ├── parser.py            # BeautifulSoup HTML extraction and pagination navigation
│   ├── transformer.py       # Data cleaning, normalization, validation, and serialization
│   └── report.py            # Automated analytical reporting and summary statistics
│
├── data/
│   ├── raw/                 # Archived raw HTML snapshots
│   │   └── .gitkeep
│   └── processed/           # Production-ready structured datasets
│       ├── tech_news.csv    # Processed CSV dataset
│       ├── tech_news.json   # Processed JSON dataset
│       └── .gitkeep
│
├── reports/
│   ├── summary.txt          # Automated execution summary and analytical report
│   └── .gitkeep
│
├── tests/
│   ├── test_parser.py       # Unit tests for HTML parsing and edge cases
│   └── test_transformer.py  # Unit tests for data transformation, deduplication, and export
│
├── main.py                  # CLI entry point and pipeline orchestrator
├── requirements.txt         # Project dependencies
├── README.md                # Project documentation
└── .gitignore               # Git exclusion rules
```

---

## Installation & Setup

### Prerequisites

- Python 3.10 or higher installed on your system.
- Git (optional, for version control).

### Step 1: Clone or Navigate to the Repository

```bash
cd automated-web-scraper
```

### Step 2: Create a Virtual Environment

It is recommended to run the project in an isolated virtual environment:

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

### Step 3: Install Required Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

## Running the Scraper

To run the complete automated pipeline with default settings:

```bash
python main.py
```

### CLI Options & Customization

The CLI supports configurable parameters for flexible execution:

```text
usage: main.py [-h] [--url URL] [--pages PAGES] [--delay DELAY] [--timeout TIMEOUT] [--verbose]

Automated Web Scraping & Data Extraction Pipeline for Tech News

options:
  -h, --help         Show this help message and exit
  --url URL          Initial entry URL to scrape (default: https://thehackernews.com/)
  --pages PAGES      Maximum number of consecutive pages to scrape (default: 2)
  --delay DELAY      Rate limiting delay in seconds between requests (default: 1.5)
  --timeout TIMEOUT  HTTP request timeout in seconds (default: 15)
  --verbose          Enable verbose debug logging
```

#### Examples:

1. **Scrape single page (fast run):**
   ```bash
   python main.py --pages 1
   ```

2. **Scrape with extended rate limit (extra polite):**
   ```bash
   python main.py --pages 3 --delay 2.5
   ```

3. **Run with verbose debug logs:**
   ```bash
   python main.py --verbose
   ```

---

## Output Files & Schema

The pipeline produces structured, analytics-ready datasets in `data/processed/`:

### 1. `data/processed/tech_news.csv`
Tabular CSV with headers:
| Field | Type | Description |
| :--- | :--- | :--- |
| `title` | String | Cleaned headline / article title |
| `url` | String | Canonical, absolute article URL |
| `published_date` | String | Date of publication (e.g. `Sep 25, 2026`) |
| `category` | String | News category / subject tag |
| `author` | String | Author name or publication credit |
| `summary` | String | Abstract or article excerpt snippet |
| `source_website` | String | Source publisher identifier (`The Hacker News`) |

### 2. `data/processed/tech_news.json`
Array of JSON objects formatted with 2-space indentation:
```json
[
  {
    "title": "Compromised GitHub Actions Came Back Online and Resumed Executing Mini Shai-Hulud Malware",
    "url": "https://thehackernews.com/2026/09/compromised-github-actions-came-back.html",
    "published_date": "Sep 25, 2026",
    "category": "Malware / Supply Chain Attack",
    "author": null,
    "summary": "Security researchers observed compromised GitHub Actions runner infrastructure resuming automated payload deployment...",
    "source_website": "The Hacker News"
  }
]
```

### 3. `reports/summary.txt`
Auto-generated analytics report detailing ingestion KPIs, category frequencies, date volume, and data completeness.

---

## Example Execution Output

When executed via terminal:

```text
========================================
AUTOMATED TECH NEWS SCRAPER
========================================

Starting scraper...
Request successful.
Articles extracted: 34
Duplicates removed: 2

CSV saved:
data/processed/tech_news.csv

JSON saved:
data/processed/tech_news.json

Summary report saved:
reports/summary.txt

Scraping completed successfully.
```

---

## Analytical Reporting

The analytical report saved in `reports/summary.txt` provides immediate executive visibility into the scraped data:

```text
==============================================================================
               AUTOMATED TECH NEWS SCRAPER - SUMMARY REPORT               
==============================================================================
Generated At      : 2026-09-25 15:40:12 UTC
Target Source     : The Hacker News (https://thehackernews.com/)
Pipeline Duration : 4.21s

------------------------------------------------------------------------------
1. INGESTION & PIPELINE METRICS
------------------------------------------------------------------------------
Total Raw Articles Extracted  : 34
Duplicate Records Removed     : 2
Invalid URLs Removed          : 0
Missing Title Records Removed : 0
Total Unique Clean Articles   : 32
Unique URLs Confirmed         : 32

------------------------------------------------------------------------------
2. CATEGORY BREAKDOWN
------------------------------------------------------------------------------
  * Malware / Supply Chain Attack            :   8 articles ( 25.0%)
  * Vulnerability / Zero-Day                 :   7 articles ( 21.9%)
  * Cyber Espionage / APT                    :   6 articles ( 18.8%)
  * Cloud Security / Infrastructure          :   5 articles ( 15.6%)
  * Artificial Intelligence / Security Ops   :   4 articles ( 12.5%)
  * Data Breach / Privacy                    :   2 articles (  6.2%)

------------------------------------------------------------------------------
3. PUBLICATION DATE BREAKDOWN
------------------------------------------------------------------------------
  * Sep 25, 2026                             :  18 articles ( 56.2%)
  * Sep 24, 2026                             :  14 articles ( 43.8%)

------------------------------------------------------------------------------
4. DATA INTEGRITY & MISSING VALUES
------------------------------------------------------------------------------
  * title                :   0 missing (  0.0%)
  * url                  :   0 missing (  0.0%)
  * published_date       :   0 missing (  0.0%)
  * category             :   0 missing (  0.0%)
  * author               :  32 missing (100.0%)
  * summary              :   0 missing (  0.0%)
  * source_website       :   0 missing (  0.0%)

------------------------------------------------------------------------------
5. SAMPLE EXTRACTED HEADLINES & INSIGHTS
------------------------------------------------------------------------------
Average Title Length: 84.6 characters

Top Recent Articles:
  [1] Compromised GitHub Actions Came Back Online and Resumed Executing Mini Shai-Hulud Malware
      Category : Malware / Supply Chain Attack | Date: Sep 25, 2026
      URL      : https://thehackernews.com/2026/09/compromised-github-actions-came-back.html
  [2] PamStealer macOS Malware Adds Live C2 Payload Decryption and Multi-Layer Persistence
      Category : Malware / Social Engineering | Date: Sep 25, 2026
      URL      : https://thehackernews.com/2026/09/pamstealer-macos-malware-adds-live-c2.html
  [3] The SOC Doesn't Need to Start Over with Every Alert
      Category : Artificial Intelligence / Security Ops | Date: Sep 25, 2026
      URL      : https://thehackernews.com/2026/09/the-soc-doesnt-need-to-start-over-with.html

==============================================================================
END OF SUMMARY REPORT
==============================================================================
```

---

## Web Scraping Ethics & Responsible Use

This project was built from the ground up to demonstrate responsible and ethical web scraping:

1. **Robots.txt Adherence**:
   The scraper verifies compliance with `https://thehackernews.com/robots.txt`. The front-page feeds and standard search listing paths are fully permitted for automated indexing under `User-agent: *`.
2. **Public Data Only**:
   The scraper accesses solely publicly available news headlines. It does not attempt to scrape private content, user profiles, or bypass authentication.
3. **No Circumvention Controls**:
   No CAPTCHA solvers, proxy rotation bypasses, or spoofing mechanisms are employed.
4. **Strict Rate Limiting**:
   A polite delay (default 1.5 seconds) is enforced between page requests, ensuring minimal server resource consumption.
5. **Transparent Identification**:
   Requests include an informative, contactable `User-Agent` header identifying the scraper as an educational internship pipeline.
6. **Local Data Caching**:
   Data is transformed and persisted locally; repeated queries avoid redundant network traffic.

---

## Testing & Quality Assurance

The codebase includes comprehensive unit tests with `pytest`. Tests use mocked HTML structures to run entirely offline, avoiding network dependencies or external rate limits.

### Running the Test Suite

```bash
pytest
```

To run with verbose output and test execution timings:

```bash
pytest -v
```

### Test Coverage Highlights

- `tests/test_parser.py`:
  - `test_parse_articles_count`: Verifies detection of valid articles and filtering of ad containers.
  - `test_parse_articles_field_extraction`: Asserts title, URL, date, category, and summary integrity.
  - `test_parse_articles_resolves_relative_url`: Validates relative-to-absolute URL conversion.
  - `test_parse_articles_handles_missing_optional_fields`: Tests resilience against missing dates/tags.
  - `test_parse_articles_empty_html`: Asserts handling of empty or blank HTML strings.
  - `test_parse_articles_malformed_html`: Asserts error-free parsing of truncated/broken markup.
  - `test_extract_next_page_url_success`: Tests pagination link detection.
  - `test_extract_next_page_url_absent`: Confirms `None` return when pager tag is absent.
- `tests/test_transformer.py`:
  - `test_clean_data_whitespace`: Verifies multi-space, tab, and newline normalization.
  - `test_duplicate_removal`: Confirms deduplication on duplicate URLs and identical titles.
  - `test_invalid_url_filtering`: Confirms rejection of `javascript:`, `#`, and invalid URLs.
  - `test_missing_field_handling`: Confirms fallback categories and tracking of missing values.
  - `test_empty_dataset`: Asserts schema preservation on empty inputs.
  - `test_save_to_csv_and_json`: Tests round-trip file serialization and verification.
  - `test_report_generation`: Validates analytical reporting metrics and output formatting.

---

## Error Handling & Reliability

The pipeline handles real-world failure modes gracefully without unhandled exceptions:

| Failure Mode | Handled By | Outcome |
| :--- | :--- | :--- |
| **Network Disconnection / DNS Failure** | `scraper.py` (`NetworkError`) | Catches `requests.ConnectionError`, displays user-friendly diagnosis, cleanly exits with code 1. |
| **Request Timeout** | `scraper.py` (`RequestTimeoutError`) | Aborts waiting after timeout threshold, reports server delay. |
| **Server Error (5xx / 429)** | `urllib3.util.retry.Retry` | Retries up to 3 times with exponential backoff before failing safely. |
| **Malformed / Truncated HTML** | `parser.py` | Safely parses partial DOM without raising parsing errors. |
| **Missing Article Elements** | `parser.py` | Extracts available fields, skips incomplete article containers. |
| **Empty Ingestion Result** | `main.py` | Checks dataset length, warns user, prevents writing corrupt files. |
| **Filesystem Write Errors** | `transformer.py`, `report.py` | Automatically creates missing directories; catches `OSError` if permissions fail. |

---

## Author & Internship Details

- **Project**: Automated Web Scraping & Data Extraction Pipeline
- **Role**: Python Software Engineering Intern
- **Focus Area**: Data Engineering, Web Scraping (ETL), Automated Reporting, Quality Assurance
