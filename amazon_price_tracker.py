"""
Amazon Price Tracker
--------------------

Lightweight scraper for Amazon product pages to extract current price, currency,
title, availability, and ASIN. Uses requests + BeautifulSoup with optional SSL controls.

Notes & disclaimers:
- This utility performs HTML scraping and may break if Amazon changes markup.
- Respect Amazon's terms of service and robots directives. Use responsibly.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Tuple, Union
import datetime as _dt
import json
import re
import time
import urllib.parse

import requests
from bs4 import BeautifulSoup


VerifyType = Optional[Union[bool, str]]
CertType = Optional[Union[str, Tuple[str, str]]]


@dataclass
class PriceInfo:
    url: str
    asin: Optional[str]
    title: Optional[str]
    price: Optional[float]
    currency: Optional[str]
    symbol: Optional[str]
    availability: Optional[str]
    timestamp: str  # ISO8601 UTC

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_NBSP = "\u00A0"


def _now_iso_utc() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat().replace("+00:00", "Z")


def _clean_text(val: Optional[str]) -> Optional[str]:
    if not val:
        return None
    s = re.sub(r"\s+", " ", val.replace(_NBSP, " ")).strip()
    return s or None


def _extract_asin(url: str, soup: Optional[BeautifulSoup] = None) -> Optional[str]:
    # From URL patterns
    m = re.search(r"/(?:dp|gp/product)/([A-Z0-9]{10})(?:/|\?|$)", url)
    if m:
        return m.group(1)
    # Hidden input
    if soup is not None:
        tag = soup.find("input", attrs={"name": "ASIN"}) or soup.find("input", id="ASIN")
        if tag and tag.get("value"):
            return tag.get("value").strip()
        # data-asin attributes
        tag = soup.find(attrs={"data-asin": True})
        if tag:
            asin = tag.get("data-asin")
            if asin and re.fullmatch(r"[A-Z0-9]{10}", asin):
                return asin
    return None


_CURRENCY_SYMBOLS = {
    "$": "USD",
    "£": "GBP",
    "€": "EUR",
    "₹": "INR",
    "¥": "JPY",
    "C$": "CAD",
    "CA$": "CAD",
    "A$": "AUD",
    "AU$": "AUD",
}


def _parse_price_and_symbol(text: str) -> Tuple[Optional[float], Optional[str]]:
    # Normalize whitespace & currency symbol prefix/suffix
    s = text.replace(_NBSP, " ").strip()
    # Capture common multi-char symbols first
    symbol = None
    for sym in sorted(_CURRENCY_SYMBOLS.keys(), key=len, reverse=True):
        if s.startswith(sym):
            symbol = sym
            s = s[len(sym):].strip()
            break
        if s.endswith(sym):
            symbol = sym
            s = s[:-len(sym)].strip()
            break
    # Remove any remaining currency or alpha chars except separators and digits
    candidate = re.sub(r"[^0-9.,]", "", s)
    if not candidate:
        return None, symbol
    # Decide decimal separator
    if "," in candidate and "." in candidate:
        # Assume dot as decimal if both present (commas thousands)
        normalized = candidate.replace(",", "")
    elif "," in candidate and "." not in candidate:
        # If last comma is decimal (1-2 digits after), treat as decimal comma
        last = candidate.rsplit(",", 1)
        if len(last[-1]) in (1, 2):
            normalized = candidate.replace(".", "").replace(",", ".")
        else:
            normalized = candidate.replace(",", "")
    else:
        normalized = candidate
    try:
        value = float(normalized)
    except ValueError:
        return None, symbol
    return value, symbol


class AmazonPriceTracker:
    def __init__(
        self,
        *,
        user_agent: Optional[str] = None,
        accept_language: Optional[str] = "en-US,en;q=0.9",
        timeout: Optional[float] = 20.0,
        verify: VerifyType = True,
        cert: CertType = None,
        max_retries: int = 2,
        backoff_factor: float = 0.5,
        proxies: Optional[Dict[str, str]] = None,
    ) -> None:
        self.session = requests.Session()
        self.timeout = timeout
        self.verify = verify
        self.cert = cert
        self.max_retries = max(0, int(max_retries))
        self.backoff_factor = max(0.0, float(backoff_factor))
        self.proxies = proxies

        self.default_headers = {
            "User-Agent": user_agent
            or (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": accept_language or "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
        }

    def _sleep_backoff(self, attempt: int) -> None:
        if self.backoff_factor <= 0:
            return
        delay = self.backoff_factor * (2 ** (attempt - 1))
        # Add a small jitter
        delay += min(0.25, self.backoff_factor / 2.0)
        time.sleep(delay)

    def fetch(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        verify: VerifyType = None,
        cert: CertType = None,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> Tuple[str, Dict[str, str]]:
        t = timeout if timeout is not None else self.timeout
        v = self.verify if verify is None else verify
        c = self.cert if cert is None else cert
        h = {**self.default_headers, **(headers or {})}
        p = proxies if proxies is not None else self.proxies

        last_exc: Optional[Exception] = None
        for attempt in range(1, self.max_retries + 2):
            try:
                resp = self.session.get(url, timeout=t, verify=v, cert=c, headers=h, proxies=p, allow_redirects=True)
                # Retry on transient status codes
                if resp.status_code in {429, 500, 502, 503, 504} and attempt <= self.max_retries + 0:
                    # Honor Retry-After header (seconds)
                    ra = resp.headers.get("Retry-After")
                    if ra and ra.isdigit():
                        time.sleep(min(10.0, float(ra)))
                    else:
                        self._sleep_backoff(attempt)
                    continue
                resp.raise_for_status()
                resp.encoding = resp.encoding or resp.apparent_encoding
                return resp.text, {k.lower(): v for k, v in resp.headers.items()}
            except requests.RequestException as e:
                last_exc = e
                if attempt > self.max_retries:
                    break
                self._sleep_backoff(attempt)
        assert last_exc is not None
        raise last_exc

    def parse(self, html: str, base_url: str) -> PriceInfo:
        soup = BeautifulSoup(html, "html.parser")

        # Title (will prefer JSON-LD name later if present)
        title = None
        t1 = soup.select_one("#productTitle")
        if t1:
            title = _clean_text(t1.get_text(" "))
        if not title:
            ogt = soup.find("meta", attrs={"property": "og:title"})
            title = _clean_text(ogt.get("content")) if ogt else None

        asin = _extract_asin(base_url, soup)

        price_val: Optional[float] = None
        currency: Optional[str] = None
        symbol: Optional[str] = None
        availability: Optional[str] = None

        # JSON-LD Product / Offer
        for script in soup.find_all("script", attrs={"type": re.compile(r"application/(ld\+json|json)", re.I)}):
            try:
                data = json.loads(script.string or "")
            except Exception:
                continue
            objs = data if isinstance(data, list) else [data]
            for obj in objs:
                if not isinstance(obj, dict):
                    continue
                types = obj.get("@type")
                if isinstance(types, list):
                    types = ",".join(types)
                if types and isinstance(types, str) and re.search(r"Product|Offer", types, re.I):
                    offers = obj.get("offers") or obj
                    if isinstance(offers, list):
                        offers = next((o for o in offers if isinstance(o, dict)), {})
                    if isinstance(offers, dict):
                        p = offers.get("price") or offers.get("lowPrice")
                        curr = offers.get("priceCurrency")
                        if p and price_val is None:
                            try:
                                price_val = float(str(p).replace(",", "."))
                            except Exception:
                                pass
                        if curr and not currency:
                            currency = str(curr)
                # Title from JSON-LD (prefer over earlier fallback)
                nm = obj.get("name")
                if isinstance(nm, str):
                    title = _clean_text(nm)
                # ASIN sometimes in sku
                if not asin:
                    sku = obj.get("sku") or obj.get("mpn")
                    if isinstance(sku, str) and re.fullmatch(r"[A-Z0-9]{10}", sku):
                        asin = sku

        # Fallback price selectors
        if price_val is None:
            selectors = [
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                "#priceblock_saleprice",
                ".a-price .a-offscreen",
                "#corePrice_feature_div .a-offscreen",
            ]
            el = None
            for sel in selectors:
                el = soup.select_one(sel)
                if el and _clean_text(el.get_text() or el.get("content")):
                    break
            if el:
                txt = _clean_text(el.get_text()) or _clean_text(el.get("content"))
                if txt:
                    val, sym = _parse_price_and_symbol(txt)
                    price_val = val if val is not None else price_val
                    symbol = sym or symbol

        # a-price whole + fraction
        if price_val is None:
            whole = soup.select_one(".a-price .a-price-whole")
            frac = soup.select_one(".a-price .a-price-fraction")
            if whole:
                w = re.sub(r"[^0-9]", "", whole.get_text())
                f = re.sub(r"[^0-9]", "", (frac.get_text() if frac else ""))
                if w:
                    try:
                        price_val = float(f"{int(w)}.{int(f) if f else 0:02d}")
                    except Exception:
                        pass

        # Availability
        av = soup.select_one("#availability .a-color-success") or soup.select_one("#availability .a-color-price") or soup.select_one("#availability")
        if av:
            availability = _clean_text(av.get_text(" "))

        # Currency symbol to ISO mapping if not provided
        if not currency and symbol:
            currency = _CURRENCY_SYMBOLS.get(symbol)

        return PriceInfo(
            url=base_url,
            asin=asin,
            title=title,
            price=price_val,
            currency=currency,
            symbol=symbol,
            availability=availability,
            timestamp=_now_iso_utc(),
        )

    def get_price(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        verify: VerifyType = None,
        cert: CertType = None,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> PriceInfo:
        html, _ = self.fetch(url, timeout=timeout, verify=verify, cert=cert, headers=headers, proxies=proxies)
        return self.parse(html, base_url=url)

    def track(
        self,
        url: str,
        *,
        persist: bool = False,
        path: Optional[str] = None,
        timeout: Optional[float] = None,
        verify: VerifyType = None,
        cert: CertType = None,
        headers: Optional[Dict[str, str]] = None,
        proxies: Optional[Dict[str, str]] = None,
    ) -> PriceInfo:
        info = self.get_price(url, timeout=timeout, verify=verify, cert=cert, headers=headers, proxies=proxies)
        if persist:
            asin = info.asin or "unknown"
            outfile = path or f"prices_{asin}.jsonl"
            line = json.dumps(info.to_dict(), ensure_ascii=False)
            # Atomic-ish append
            with open(outfile, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        return info
