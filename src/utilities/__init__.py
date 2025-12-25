"""
Python Utilities
================

A collection of lightweight, reusable utilities for common Python tasks.

Modules:
- file_utils: File I/O and filesystem operations
- rest_client: REST API client with SSL support
- news_scraper: Web scraping for articles and news
- amazon_price_tracker: Amazon product price tracking
- video_filename_fixer: Video file renaming utility

All utilities are dependency-light and easy to integrate into other projects.
"""

__version__ = "1.0.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from python_utilities.file_utils import FileUtils
from python_utilities.rest_client import RestClient
from python_utilities.news_scraper import NewsScraper, Article
from python_utilities.amazon_price_tracker import AmazonPriceTracker, PriceInfo
from python_utilities.video_filename_fixer import VideoFilenameFixer

__all__ = [
    "FileUtils",
    "RestClient",
    "NewsScraper",
    "Article",
    "AmazonPriceTracker",
    "PriceInfo",
    "VideoFilenameFixer",
    "__version__",
]
