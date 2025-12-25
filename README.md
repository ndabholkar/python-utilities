# Python Utilities

[![Python Versions](https://img.shields.io/pypi/pyversions/python-utilities.svg)](https://pypi.org/project/python-utilities/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A collection of lightweight, reusable utilities for common Python tasks including file I/O, REST APIs, web scraping, Amazon price tracking, and video file management.

## Overview

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

## Installation

### From PyPI (when published)

```bash
pip install python-utilities
```

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/python-utilities.git
cd python-utilities

# Install in editable mode with dev dependencies
pip install -e ".[dev]"

# Or install only runtime dependencies
pip install -e .
```

## Requirements

- Python 3.8 or higher
- `requests>=2.28.0` (for RestClient, NewsScraper, AmazonPriceTracker)
- `beautifulsoup4>=4.11.0` (for NewsScraper, AmazonPriceTracker)
- FileUtils and VideoFilenameFixer use only the Python standard library (no extra dependencies)

## Project Structure

This project follows modern Python packaging standards (PyPA):

```
python-utilities/
├── src/
│   └── python_utilities/         # Package directory (src/ layout)
│       ├── __init__.py           # Package initialization
│       ├── file_utils.py         # File I/O utilities
│       ├── rest_client.py        # REST API client
│       ├── news_scraper.py       # News/article scraper
│       ├── amazon_price_tracker.py  # Amazon price tracker
│       ├── video_filename_fixer.py  # Video renaming utility
│       └── py.typed              # PEP 561 type hints marker
├── tests/
│   ├── test_file_utils.py        # FileUtils tests
│   ├── test_rest_client.py       # RestClient tests
│   ├── test_news_scraper.py      # NewsScraper tests
│   ├── test_amazon_price_tracker.py  # Price tracker tests
│   └── test_video_filename_fixer.py  # Video fixer tests
├── pyproject.toml                # PEP 621 project metadata
├── README.md                     # This file
├── LICENSE                       # MIT License
├── .gitignore                    # Git ignore patterns
└── PACKAGING.md                  # Packaging/publishing guide
```

## Usage Examples

### FileUtils

```python
from python_utilities import FileUtils

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

### RestClient

```python
from python_utilities import RestClient

client = RestClient(
    base_url="https://api.example.com",
    default_headers={"Authorization": "Bearer TOKEN"},
    verify=True,  # or False, or path to a CA bundle
    cert=None,  # or "/path/to/client.crt" or ("/path/to/cert.crt", "/path/to/key.key")
)

# GET with query params
items = client.get("/v1/items", params={"page": 1, "limit": 20})

# POST with a JSON body
created = client.post("/v1/items", json_body={"name": "foo"})

# Handle errors without raising
result = client.get("/v1/might-404", raise_for_status=False)  # returns None on 404
```

### NewsScraper

```python
from python_utilities import NewsScraper

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

### AmazonPriceTracker

```python
from python_utilities import AmazonPriceTracker

tracker = AmazonPriceTracker(timeout=20, verify=True)
url = "https://www.amazon.com/dp/B08N5WRWNW"  # replace with your product URL

# Get current price info
info = tracker.get_price(url)
print(info.to_dict())

# Persist to JSONL for price history
info = tracker.track(url, persist=True, path="prices_B08N5WRWNW.jsonl")
```

### VideoFilenameFixer

```python
from python_utilities import VideoFilenameFixer
from pathlib import Path

# Quick usage with the convenience function
# Preview changes without renaming (dry-run mode)
from python_utilities.video_filename_fixer import fix_video_filenames
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
    verbose=True  # print log messages
)

# Check results programmatically
for result in results:
    if result.success:
        print(f"✓ {result.original_path.name} → {result.new_path.name}")
    else:
        print(f"✗ {result.original_path.name}: {result.error_message}")
```

**Example transformation:**
```
Before:                          After:
1. Introduction.mp4       →      001. Introduction.mp4
2 - Basics.mp4            →      002 - Basics.mp4
10 Advanced.mp4           →      010 Advanced.mp4
42. Expert Level.avi      →      042. Expert Level.avi
```

## Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/python-utilities.git
cd python-utilities

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1

# Install in editable mode with dev dependencies
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=utilities --cov-report=html

# Run specific test file
pytest tests/test_file_utils.py

# Run with verbose output
pytest -v
```

### Code Quality

```bash
# Lint with Ruff
ruff check src/ tests/

# Auto-fix issues
ruff check --fix src/ tests/

# Format code
ruff format src/ tests/

# Type check with mypy
mypy src/
```

### Building the Package

```bash
# Install build tool
pip install build

# Build source distribution and wheel
python -m build

# Check the distribution
pip install twine
twine check dist/*
```

## SSL/TLS Options

All HTTP utilities (RestClient, NewsScraper, AmazonPriceTracker) expose SSL options like `requests` does:

- **verify** — bool or path to a CA bundle file. Set to False to skip certificate verification (not recommended for production).
- **cert** — path to a client certificate, or a (cert, key) tuple.

You can set these at the instance level and override them per call/scrape:

```python
from python_utilities import RestClient, NewsScraper, AmazonPriceTracker

# Create instances with SSL options
client = RestClient(base_url="https://api.example.com", verify=True)
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

## Running Tests

This package uses pytest (modern testing framework):

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=utilities --cov-report=html
```

**Note**: Old unittest-style tests are being migrated to pytest. See [tests/](tests/) directory.

## Why This Structure?

This project follows modern Python packaging standards:

- **PEP 621**: Project metadata in `pyproject.toml` (replaces setup.py/setup.cfg)
- **PEP 517/518**: Modern build system with Hatchling
- **src/ layout**: Package isolation for better testing
- **py.typed**: Type hint support (PEP 561) for IDE autocomplete and mypy
- **Modern tooling**: Ruff (linting), pytest (testing), mypy (type checking)

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes and add tests
4. Run tests and linting (`pytest && ruff check`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built following [PyPA](https://www.pypa.io/) packaging best practices
- Inspired by the need for lightweight, reusable Python utilities
- Uses modern Python packaging standards (PEP 621, PEP 517/518, PEP 561)

## Resources

- [Python Packaging User Guide](https://packaging.python.org/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
- [requests Documentation](https://docs.python-requests.org/)
- [Beautiful Soup Documentation](https://www.crummy.com/software/BeautifulSoup/)

## Authors

- Your Name - *Initial work* - [yourusername](https://github.com/yourusername)
