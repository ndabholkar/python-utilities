import unittest
from typing import Any

import types

# Detect availability of BeautifulSoup before importing the scraper
try:
    import bs4  # noqa: F401
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

if HAS_BS4:
    from news_scraper import NewsScraper, Article


class DummyResponse:
    def __init__(self, url: str, text: str, status_code: int = 200, headers: dict | None = None, encoding: str | None = "utf-8"):
        self.url = url
        self.text = text
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "text/html; charset=utf-8"}
        self.encoding = encoding
        self.apparent_encoding = encoding

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


@unittest.skipUnless(HAS_BS4, "beautifulsoup4 is required for NewsScraper tests")
class NewsScraperTest(unittest.TestCase):
    def test_parse_jsonld_article(self):
        html = (
            """
            <html><head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "NewsArticle",
              "headline": "Test Headline",
              "description": "Short description",
              "datePublished": "2025-01-01T10:00:00Z",
              "author": {"@type": "Person", "name": "Jane Doe"},
              "image": {"@type": "ImageObject", "url": "/img/cover.jpg"}
            }
            </script>
            </head><body><article><p>Paragraph 1.</p><p>Paragraph 2.</p></article></body></html>
            """
        )
        scraper = NewsScraper()
        article = scraper.parse(html, base_url="https://example.com/news/test")
        self.assertIsInstance(article, Article)
        self.assertEqual(article.title, "Test Headline")
        self.assertEqual(article.author, "Jane Doe")
        self.assertEqual(article.published_at, "2025-01-01T10:00:00Z")
        self.assertEqual(article.top_image, "https://example.com/img/cover.jpg")
        self.assertTrue(article.content.startswith("Paragraph 1."))

    def test_parse_opengraph_fallback(self):
        html = (
            """
            <html><head>
              <meta property="og:title" content="OG Title" />
              <meta property="og:description" content="OG Description" />
              <meta property="article:published_time" content="2024-12-12T09:30:00Z" />
              <meta property="og:image" content="/images/og.jpg" />
            </head>
            <body>
              <main><p>Body text paragraph.</p></main>
            </body></html>
            """
        )
        scraper = NewsScraper()
        article = scraper.parse(html, base_url="https://site.test/path/page")
        self.assertEqual(article.title, "OG Title")
        self.assertEqual(article.description, "OG Description")
        self.assertEqual(article.published_at, "2024-12-12T09:30:00Z")
        self.assertEqual(article.top_image, "https://site.test/images/og.jpg")
        self.assertIn("Body text paragraph.", article.content or "")

    def test_fetch_ssl_options_passed(self):
        # Monkeypatch the session.get to capture parameters
        scraper = NewsScraper(verify=True, cert=None)
        captured: dict[str, Any] = {}

        def fake_get(self, url, **kwargs):  # type: ignore[no-redef]
            captured.update(kwargs)
            return DummyResponse(url=url, text="<html></html>")

        scraper._session.get = types.MethodType(fake_get, scraper._session)

        _html, _url, _headers = scraper.fetch(
            "https://example.org/article",
            timeout=7.5,
            verify=False,
            cert=("/path/cert.pem", "/path/key.pem"),
        )
        self.assertEqual(captured.get("timeout"), 7.5)
        self.assertEqual(captured.get("verify"), False)
        self.assertEqual(captured.get("cert"), ("/path/cert.pem", "/path/key.pem"))
        self.assertTrue(captured.get("allow_redirects"))

    def test_scrape_uses_fetch_and_parse(self):
        scraper = NewsScraper()

        html = """
        <html><head><title>Just a Title</title></head>
        <body><article><p>Hello world.</p></article></body></html>
        """

        def fake_get(self, url, **kwargs):  # type: ignore[no-redef]
            return DummyResponse(url="https://example.com/article", text=html)

        scraper._session.get = types.MethodType(fake_get, scraper._session)

        art = scraper.scrape("https://example.com/article")
        self.assertEqual(art.url, "https://example.com/article")
        self.assertEqual(art.title, "Just a Title")
        self.assertIn("Hello world.", art.content or "")


if __name__ == "__main__":
    unittest.main()
