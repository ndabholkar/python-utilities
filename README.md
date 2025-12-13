Python Utilities — REST Client and News Scraper

Overview

This repository provides two small, reusable utilities built on top of the requests and beautifulsoup4 libraries:

- RestClient — a lightweight helper for calling REST APIs with all common HTTP methods, query parameters, JSON payloads, and SSL options.
- NewsScraper — a generic news/article scraper that extracts metadata and readable content from web pages, with SSL options.

Both components are dependency‑light, easy to embed into other projects, and come with unit tests.

Features

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

Project structure

```
.
├── guardian_article.json          # Example saved output from NewsScraper
├── main.py                        # Optional entry point / example (if used)
├── news_scraper.py                # NewsScraper implementation
├── rest_client.py                 # RestClient implementation
└── tests
    ├── test_news_scraper.py
    └── test_rest_client.py
```

Requirements

- Python 3.8+
- requests
- beautifulsoup4 (only required for the scraper)

Install dependencies

You can install the minimal dependencies directly:

```
pip install requests beautifulsoup4
```

Quick start

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

SSL/TLS options

Both utilities expose SSL options like requests does:

- verify — bool or path to a CA bundle file. Set to False to skip certificate verification (not recommended for production).
- cert — path to a client certificate, or a (cert, key) tuple.

You can set these at the instance level and override them per call/scrape:

```python
from rest_client import RestClient
from news_scraper import NewsScraper

# Create instances (can also be created once and reused)
client = RestClient(base_url="https://api.example.com")
scraper = NewsScraper(timeout=15, verify=True)

# Per-call overrides
client.get("/secure", verify=False)

article = scraper.scrape(
    "https://news.example.org/post",
    verify="/path/to/custom-ca.pem",
    cert=("/path/to/client.crt", "/path/to/client.key"),
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

License

Add your license of choice here (e.g., MIT). If none is provided, all rights reserved by default.
