Python Utilities — REST Client, News Scraper, Amazon Price Tracker, File Utilities, and Video Filename Fixer

Overview

This repository provides five small, reusable utilities:

- FileUtils — stdlib-only helpers for file IO (text/bytes/JSON/lines), atomic writes, filesystem operations, hashing, and path helpers.
- RestClient — a lightweight helper for calling REST APIs with all common HTTP methods, query parameters, JSON payloads, and SSL options (requests-based).
- NewsScraper — a generic news/article scraper that extracts metadata and readable content from web pages, with SSL options (requests + beautifulsoup4).
- AmazonPriceTracker — a lightweight price tracker that scrapes Amazon product pages to extract price, currency, title, availability, and ASIN. Supports retries, SSL options, and optional JSONL persistence for history (requests + beautifulsoup4).
- VideoFilenameFixer — a stdlib-only utility for fixing the ordering of offline video tutorial files by renaming them with zero-padded numbers at the start of their filenames.

All utilities are dependency‑light, easy to embed into other projects, and come with unit tests.

Features

FileUtils

- Read/Write: text, bytes, and lines (encoding/newline options)
- JSON helpers: read_json, write_json (indent/ensure_ascii/sort_keys)
- Atomic writes: atomic_write_text/bytes/json (same-dir temp + fsync + os.replace)
- Filesystem ops: exists, is_file, is_dir, size, touch, mkdirs, listdir, glob, remove (missing_ok), rmtree (missing_ok), copy, move, rename
- Hashing: sha256_file, md5_file (chunked)
- Path helpers: resolve (relative to optional base_dir), expanduser, ensure_suffix, change_ext
- Temporary directory: temporary_directory() context manager (yields a Path)

RestClient

- Supports GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS
- Query parameters via params and JSON payloads via json_body
- Merges default headers with per‑request headers
- Sensible defaults: Accept: application/json and Content‑Type set automatically when sending JSON
- Returns parsed JSON for JSON responses; returns None for empty or non‑JSON responses
- Error handling: raises for non‑2xx by default (requests.exceptions.HTTPError); can be disabled per call
- SSL/TLS: verify (bool or CA bundle path) and cert (client cert path or (cert, key) tuple) at client level and per call

NewsScraper

- Persistent requests.Session with configurable timeout
- SSL/TLS: verify and cert supported per instance and per scrape
- Extraction strategy:
  1) JSON‑LD (Schema.org Article/NewsArticle) when available
  2) Open Graph/Twitter Card meta tags
  3) Fallbacks: title, h1, and article/body paragraphs
- Collects primary/top image and additional images referenced on the page
- Returns a structured Article dataclass

AmazonPriceTracker

- Requests + BeautifulSoup with realistic default headers
- Retry with basic exponential backoff on transient errors (429/5xx)
- SSL/TLS: verify and cert supported per instance and per call
- Optional proxies support
- Extracts from JSON‑LD (Product/Offer) when available, with DOM fallbacks:
  - Selectors like #priceblock_ourprice, .a-price .a-offscreen, and whole+fraction
- Returns a structured PriceInfo dataclass
- Optional persistence to JSONL via track(..., persist=True)

VideoFilenameFixer

- Recursively traverses directories to find video files
- Detects filenames starting with 1-2 digits followed by separators (., space, dash, or combinations)
- Renames files with 3-digit zero-padded numbers (configurable padding width)
- Handles all common video file extensions (.mp4, .avi, .mkv, .mov, etc.)
- Dry-run mode to preview changes without renaming
- Clear logging of all rename operations
- Returns structured RenameResult objects for programmatic use
- No external dependencies (stdlib only)

Project structure

```
.
├── main.py                        # Optional entry point / example (if used)
├── file_utils.py                  # FileUtils implementation
├── amazon_price_tracker.py        # AmazonPriceTracker implementation
├── news_scraper.py                # NewsScraper implementation
├── rest_client.py                 # RestClient implementation
├── video_filename_fixer.py        # VideoFilenameFixer implementation
└── tests
    ├── test_amazon_price_tracker.py
    ├── test_file_utils.py
    ├── test_news_scraper.py
    ├── test_rest_client.py
    └── test_video_filename_fixer.py
```

Requirements

- Python 3.8+
- requests
- beautifulsoup4 (required for the scrapers: NewsScraper and AmazonPriceTracker)
- FileUtils and VideoFilenameFixer use only the Python standard library (no extra dependencies)

Install dependencies

You can install the minimal dependencies directly:

```
pip install requests beautifulsoup4
```

Quick start

FileUtils

```python
from file_utils import FileUtils

fs = FileUtils(base_dir="./data")

# Text IO
fs.write_text("notes/todo.txt", "- buy milk\n")
print(fs.read_text("notes/todo.txt"))

# JSON (atomic)
cfg = {"env": "dev", "retries": 3}
fs.atomic_write_json("config/app.json", cfg)
print(fs.read_json("config/app.json"))

# Filesystem ops and hashing
fs.mkdirs("outputs")
fs.copy("config/app.json", "outputs/app-copy.json")
print(fs.sha256_file("outputs/app-copy.json"))

# Temporary directory
from pathlib import Path
with fs.temporary_directory(prefix="tmp_") as td:
    p = td / "temp.txt"
    p.write_text("hi", encoding="utf-8")
    assert p.exists()
```

RestClient

```python
from rest_client import RestClient

client = RestClient(
    base_url="https://api.example.com",
    default_headers={"Authorization": "Bearer TOKEN"},
    verify=True,  # or False, or path to a CA bundle
    cert=None,    # or "/path/to/client.crt" or ("/path/to/cert.crt", "/path/to/key.key")
)

# GET with query params
items = client.get("/v1/items", params={"page": 1, "limit": 20})

# POST with a JSON body
created = client.post("/v1/items", json_body={"name": "foo"})

# Handle errors without raising
result = client.get("/v1/might-404", raise_for_status=False)  # returns None on 404
```

NewsScraper

```python
from news_scraper import NewsScraper

scraper = NewsScraper(timeout=15, verify=True)
article = scraper.scrape("https://example.com/news/some-article")

print(article.title)
print(article.published_at)
print(article.author)
print(article.content)
print(article.top_image)

# Convert to a plain dict or JSON
d = article.to_dict()
```

AmazonPriceTracker

```python
from amazon_price_tracker import AmazonPriceTracker

tracker = AmazonPriceTracker(timeout=20, verify=True)
url = "https://www.amazon.com/dp/B08N5WRWNW"  # replace with your product URL

# Get current price info
info = tracker.get_price(url)
print(info.to_dict())

# Persist to JSONL for price history
info = tracker.track(url, persist=True, path="prices_B08N5WRWNW.jsonl")
```

VideoFilenameFixer

```python
from video_filename_fixer import VideoFilenameFixer, fix_video_filenames

# Quick usage with the convenience function
# Preview changes without renaming (dry-run mode)
results = fix_video_filenames("/path/to/tutorials", dry_run=True)

# Actually rename files recursively
results = fix_video_filenames("/path/to/tutorials", dry_run=False)

# Using the class for more control
fixer = VideoFilenameFixer(
    padding_width=3,  # 3-digit padding (default)
    dry_run=False,
    video_extensions={'.mp4', '.avi', '.mkv', '.mov'}  # optional: customize
)

# Process a directory
results = fixer.fix_directory(
    "/path/to/tutorials",
    recursive=True,  # process subdirectories
    verbose=True     # print log messages
)

# Check results programmatically
for result in results:
    if result.success:
        print(f"✓ {result.original_path.name} → {result.new_path.name}")
    else:
        print(f"✗ {result.original_path.name}: {result.error_message}")

# Command-line usage
# python video_filename_fixer.py /path/to/tutorials --dry-run
# python video_filename_fixer.py /path/to/tutorials
```

Example transformation:
```
Before:                          After:
1. Introduction.mp4       →      001. Introduction.mp4
2 - Basics.mp4            →      002 - Basics.mp4
10 Advanced.mp4           →      010 Advanced.mp4
42. Expert Level.avi      →      042. Expert Level.avi
```

SSL/TLS options

All HTTP utilities here (RestClient, NewsScraper, AmazonPriceTracker) expose SSL options like requests does:

- verify — bool or path to a CA bundle file. Set to False to skip certificate verification (not recommended for production).
- cert — path to a client certificate, or a (cert, key) tuple.

You can set these at the instance level and override them per call/scrape:

```python
from rest_client import RestClient
from news_scraper import NewsScraper
from amazon_price_tracker import AmazonPriceTracker

# Create instances (can also be created once and reused)
client = RestClient(base_url="https://api.example.com")
scraper = NewsScraper(timeout=15, verify=True)
tracker = AmazonPriceTracker(timeout=20, verify=True)

# Per-call overrides
client.get("/secure", verify=False)

article = scraper.scrape(
    "https://news.example.org/post",
    verify="/path/to/custom-ca.pem",
    cert=("/path/to/client.crt", "/path/to/client.key"),
)

# Per-call overrides for AmazonPriceTracker (with proxy)
price = tracker.get_price(
    "https://www.amazon.com/dp/B08N5WRWNW",
    verify=False,
    cert=("/path/to/client.crt", "/path/to/client.key"),
    proxies={"https": "http://proxy.example:8080"},
)
```

Running tests

This repository uses the standard unittest runner.

```
python -m unittest discover -s tests -v
```

Notes

- RestClient returns None when the response is empty (e.g., 204) or not JSON.
- NewsScraper prioritizes structured metadata (JSON‑LD, Open Graph). It then falls back to common HTML patterns to assemble content.
- If beautifulsoup4 is not installed, scraper tests may be skipped; install it to run all tests.
- AmazonPriceTracker scrapes HTML and can be affected by anti‑bot measures and markup changes. Use realistic headers, backoff on 429/5xx, and consider proxies if appropriate and permitted.

Example: save a scraped article to JSON

```python
import json
from news_scraper import NewsScraper

url = "https://www.theguardian.com/world/2025/dec/12/uk-sanctions-four-rsf-commanders-heinous-violence-against-sudan-civilians"
scraper = NewsScraper(timeout=25, verify=True)
article = scraper.scrape(url)

with open("guardian_article.json", "w", encoding="utf-8") as f:
    json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)
```

Troubleshooting

- SSL certificate verify failed — Provide a custom CA bundle via verify="/path/to/ca.pem", or temporarily set verify=False for testing. On macOS, ensure Certificates are up to date.
- Non‑JSON API responses — RestClient intentionally returns None unless the Content‑Type indicates JSON.
- Site‑specific scraping edge cases — News websites vary widely. For higher accuracy on a specific site, consider adding a site‑specific parser.
- Amazon 429/503 or blocks — Reduce request rate, increase backoff, ensure a desktop User‑Agent and Accept‑Language are set (the tracker does this by default), and consider using region‑appropriate proxies where allowed.

License

Add your license of choice here (e.g., MIT). If none is provided, all rights reserved by default.
