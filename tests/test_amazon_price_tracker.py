import unittest
from typing import Any
import types
import json
import tempfile
import os

# Detect availability of BeautifulSoup before importing the scraper
try:
    import bs4  # noqa: F401
    HAS_BS4 = True
except Exception:
    HAS_BS4 = False

if HAS_BS4:
    from amazon_price_tracker import AmazonPriceTracker, PriceInfo


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


@unittest.skipUnless(HAS_BS4, "beautifulsoup4 is required for AmazonPriceTracker tests")
class AmazonPriceTrackerTest(unittest.TestCase):
    def test_parse_jsonld_product(self):
        html = (
            """
            <html><head>
            <script type="application/ld+json">
            {
              "@context": "https://schema.org",
              "@type": "Product",
              "name": "Sample Product",
              "sku": "B012345678",
              "offers": {"@type": "Offer", "price": "19.99", "priceCurrency": "USD"}
            }
            </script>
            </head><body>
            <span id="productTitle">Sample Product Title</span>
            </body></html>
            """
        )
        tracker = AmazonPriceTracker()
        info = tracker.parse(html, base_url="https://www.amazon.com/dp/B012345678")
        self.assertIsInstance(info, PriceInfo)
        self.assertEqual(info.asin, "B012345678")
        self.assertEqual(info.title, "Sample Product")  # JSON-LD name preferred
        self.assertEqual(info.currency, "USD")
        self.assertAlmostEqual(info.price or 0.0, 19.99, places=2)

    def test_parse_price_selectors_and_symbol(self):
        html = (
            """
            <html><head><meta property="og:title" content="OG Title"/></head>
            <body>
            <span id="priceblock_ourprice">£12.34</span>
            <div id="availability"><span class="a-color-success">In Stock.</span></div>
            </body></html>
            """
        )
        tracker = AmazonPriceTracker()
        info = tracker.parse(html, base_url="https://www.amazon.co.uk/dp/B000000001")
        self.assertEqual(info.symbol, "£")
        self.assertEqual(info.currency, "GBP")
        self.assertAlmostEqual(info.price or 0.0, 12.34, places=2)
        self.assertIn("In Stock", info.availability or "")

    def test_parse_aprice_whole_fraction(self):
        html = (
            """
            <html><body>
              <span class="a-price"><span class="a-offscreen">$1,234.56</span>
                <span class="a-price-whole">1,234</span>
                <span class="a-price-fraction">56</span>
              </span>
            </body></html>
            """
        )
        tracker = AmazonPriceTracker()
        info = tracker.parse(html, base_url="https://www.amazon.com/gp/product/B08N5WRWNW")
        self.assertAlmostEqual(info.price or 0.0, 1234.56, places=2)

    def test_fetch_ssl_and_retry(self):
        tracker = AmazonPriceTracker(verify=True, cert=None, max_retries=1, backoff_factor=0.0)
        captured: dict[str, Any] = {}

        calls: list[DummyResponse] = [
            DummyResponse(url="https://a/1", text="<html></html>", status_code=503),
            DummyResponse(url="https://a/1", text="<html><span id='priceblock_ourprice'>$9.99</span></html>", status_code=200),
        ]

        def fake_get(self, url, **kwargs):  # type: ignore[no-redef]
            captured.update(kwargs)
            return calls.pop(0)

        tracker.session.get = types.MethodType(fake_get, tracker.session)

        html, headers = tracker.fetch(
            "https://www.amazon.com/dp/B012345678",
            timeout=7.0,
            verify=False,
            cert=("/path/cert.pem", "/path/key.pem"),
            headers={"X-Test": "1"},
            proxies={"https": "http://proxy:8080"},
        )
        self.assertIn("priceblock_ourprice", html)
        self.assertEqual(captured.get("timeout"), 7.0)
        self.assertEqual(captured.get("verify"), False)
        self.assertEqual(captured.get("cert"), ("/path/cert.pem", "/path/key.pem"))
        self.assertTrue(captured.get("allow_redirects"))
        self.assertEqual(captured.get("proxies"), {"https": "http://proxy:8080"})
        self.assertIn("headers", captured)
        self.assertEqual(captured["headers"].get("X-Test"), "1")
        self.assertIn("User-Agent", captured["headers"])  # default header merged

    def test_track_persist_jsonl(self):
        html = """
        <html><body>
          <span id="productTitle">Widget</span>
          <span id="priceblock_ourprice">$5.00</span>
        </body></html>
        """
        tracker = AmazonPriceTracker()

        def fake_get(self, url, **kwargs):  # type: ignore[no-redef]
            return DummyResponse(url=url, text=html)

        tracker.session.get = types.MethodType(fake_get, tracker.session)

        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "prices_test.jsonl")
            info = tracker.track("https://www.amazon.com/dp/B0TEST0000", persist=True, path=path)
            self.assertTrue(os.path.exists(path))
            with open(path, "r", encoding="utf-8") as f:
                lines = [json.loads(l) for l in f.read().strip().splitlines() if l.strip()]
            self.assertEqual(len(lines), 1)
            self.assertEqual(lines[0]["title"], info.title)
            self.assertAlmostEqual(float(lines[0]["price"]), 5.00, places=2)


if __name__ == "__main__":
    unittest.main()
