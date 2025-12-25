"""
News web scraper utility using `requests` and `beautifulsoup4` with SSL handling.

Capabilities:
- Fetches HTML with `requests.Session`, supporting SSL options `verify` and `cert` (bool/path and cert path or tuple)
- Parses article metadata using multiple signals in priority order:
  1) JSON-LD (Schema.org `Article`/`NewsArticle`)
  2) OpenGraph and Twitter Card meta tags
  3) Fallback: <title>, <h1>, and main/article paragraph text

Returns a structured `Article` dataclass. Designed to be lightweight and generic; no site-specific adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Union
import json
import re
import urllib.parse

import requests
from bs4 import BeautifulSoup


VerifyType = Optional[Union[bool, str]]
CertType = Optional[Union[str, Tuple[str, str]]]


@dataclass
class Article:
    url: str
    source: Optional[str] = None
    title: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[str] = None  # ISO8601 string if available
    description: Optional[str] = None
    content: Optional[str] = None
    top_image: Optional[str] = None
    images: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _clean_text(text: Optional[str]) -> Optional[str]:
    if not text:
        return None
    t = re.sub(r"\s+", " ", text).strip()
    return t or None


def _first(*values: Optional[str]) -> Optional[str]:
    for v in values:
        if v and v.strip():
            return v.strip()
    return None


def _get_meta(soup: BeautifulSoup, *, name: Optional[str] = None, prop: Optional[str] = None) -> Optional[str]:
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return tag.get("content")
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return tag.get("content")
    return None


def _resolve_url(url: Optional[str], base: str) -> Optional[str]:
    if not url:
        return None
    return urllib.parse.urljoin(base, url)


def _iter_jsonld_objects(soup: BeautifulSoup):
    for script in soup.find_all("script", attrs={"type": re.compile(r"application/(ld\+json|json)", re.I)}):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        if isinstance(data, list):
            for item in data:
                yield item
        elif isinstance(data, dict):
            # Some pages wrap graph in @graph
            if "@graph" in data and isinstance(data["@graph"], list):
                for item in data["@graph"]:
                    yield item
            else:
                yield data


def _pick_article_obj(objs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for obj in objs:
        t = obj.get("@type")
        if not t:
            continue
        if isinstance(t, list):
            types = [str(x).lower() for x in t]
        else:
            types = [str(t).lower()]
        if any(x in ("article", "newsarticle", "blogposting") for x in types):
            return obj
    return None


class NewsScraper:
    def __init__(
        self,
        *,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = 20.0,
        verify: VerifyType = True,
        cert: CertType = None,
    ) -> None:
        self._session = requests.Session()
        self.timeout = timeout
        self.verify = verify
        self.cert = cert
        self._session.headers.update(
            {
                "User-Agent": user_agent
                or "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36 PythonNewsScraper/1.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )

    def fetch(self, url: str, *, timeout: Optional[float] = None, verify: VerifyType = None, cert: CertType = None) -> Tuple[str, str, Dict[str, str]]:
        effective_timeout = self.timeout if timeout is None else timeout
        effective_verify = self.verify if verify is None else verify
        effective_cert = self.cert if cert is None else cert

        resp = self._session.get(
            url,
            timeout=effective_timeout,
            verify=effective_verify,
            cert=effective_cert,
            allow_redirects=True,
        )
        resp.raise_for_status()
        # Try to determine encoding if not provided
        if not resp.encoding:
            resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
        final_url = resp.url
        headers = {k: v for k, v in resp.headers.items()}
        return html, final_url, headers

    def parse(self, html: str, base_url: str, response_headers: Optional[Dict[str, str]] = None) -> Article:
        soup = BeautifulSoup(html, "html.parser")

        # Source / site name
        site_name = _first(
            _get_meta(soup, prop="og:site_name"),
            _get_meta(soup, name="application-name"),
            _get_meta(soup, name="twitter:site"),
        )

        # JSON-LD
        jsonld_objs = list(_iter_jsonld_objects(soup))
        article_obj = _pick_article_obj(jsonld_objs) if jsonld_objs else None
        title_ld = None
        author_ld = None
        published_ld = None
        description_ld = None
        image_ld = None
        if isinstance(article_obj, dict):
            title_ld = article_obj.get("headline") or article_obj.get("name")
            desc_candidate = article_obj.get("description")
            if isinstance(desc_candidate, dict):
                description_ld = desc_candidate.get("@value") or desc_candidate.get("text")
            else:
                description_ld = desc_candidate
            author_field = article_obj.get("author")
            if isinstance(author_field, list):
                names = []
                for a in author_field:
                    if isinstance(a, dict):
                        n = a.get("name") or a.get("@id")
                        if n:
                            names.append(str(n))
                    elif isinstance(a, str):
                        names.append(a)
                author_ld = ", ".join([x for x in names if x]) or None
            elif isinstance(author_field, dict):
                author_ld = author_field.get("name") or author_field.get("@id")
            elif isinstance(author_field, str):
                author_ld = author_field
            published_ld = (
                article_obj.get("datePublished")
                or article_obj.get("dateCreated")
                or article_obj.get("dateModified")
            )
            image_field = article_obj.get("image")
            if isinstance(image_field, dict):
                image_ld = image_field.get("url") or image_field.get("contentUrl")
            elif isinstance(image_field, list) and image_field:
                first_img = image_field[0]
                if isinstance(first_img, dict):
                    image_ld = first_img.get("url") or first_img.get("contentUrl")
                else:
                    image_ld = str(first_img)
            elif isinstance(image_field, str):
                image_ld = image_field

        # OpenGraph / Twitter
        title_og = _first(_get_meta(soup, prop="og:title"), _get_meta(soup, name="twitter:title"))
        desc_og = _first(_get_meta(soup, prop="og:description"), _get_meta(soup, name="twitter:description"))
        author_meta = _first(_get_meta(soup, name="author"), _get_meta(soup, name="article:author"))
        published_meta = _first(
            _get_meta(soup, prop="article:published_time"),
            _get_meta(soup, name="pubdate"),
            _get_meta(soup, name="date"),
            _get_meta(soup, prop="og:updated_time"),
        )
        image_og = _first(_get_meta(soup, prop="og:image"), _get_meta(soup, name="twitter:image"))

        # Title fallbacks
        title_tag = None
        if soup.title and soup.title.string:
            title_tag = soup.title.string
        h1 = soup.find("h1")
        h1_text = h1.get_text(separator=" ", strip=True) if h1 else None

        # Content extraction (simple heuristic)
        article_nodes = soup.find_all(["article", "main"]) or []
        content_text = None
        nodes_to_scan = article_nodes or [soup.body] if soup.body else []
        paras: List[str] = []
        for node in nodes_to_scan:
            if not node:
                continue
            for p in node.find_all("p"):
                txt = _clean_text(p.get_text(" "))
                if txt:
                    paras.append(txt)
            # If enough text collected, stop
            if sum(len(x) for x in paras) > 500:
                break
        if paras:
            content_text = "\n\n".join(paras)

        # Images
        images: List[str] = []
        for sel in [
            ("meta", {"property": "og:image"}, "content"),
            ("meta", {"name": "twitter:image"}, "content"),
        ]:
            tag = soup.find(sel[0], attrs=sel[1])
            if tag and tag.get(sel[2]):
                resolved = _resolve_url(tag.get(sel[2]), base_url)
                if resolved:
                    images.append(resolved)
        # Also collect a few <img> inside article/main
        for node in article_nodes:
            for img in node.find_all("img"):
                src = img.get("src") or img.get("data-src")
                resolved = _resolve_url(src, base_url)
                if resolved:
                    images.append(resolved)
        # Deduplicate preserving order
        seen = set()
        dedup_images = []
        for u in images:
            if u not in seen:
                seen.add(u)
                dedup_images.append(u)

        article = Article(
            url=base_url,
            source=_clean_text(site_name),
            title=_clean_text(_first(title_ld, title_og, title_tag, h1_text)),
            author=_clean_text(_first(author_ld, author_meta)),
            published_at=_clean_text(_first(published_ld, published_meta)),
            description=_clean_text(_first(description_ld, desc_og)),
            content=_clean_text(content_text),
            top_image=_resolve_url(_first(image_ld, image_og, dedup_images[0] if dedup_images else None), base_url),
            images=dedup_images,
        )

        return article

    def scrape(
        self,
        url: str,
        *,
        timeout: Optional[float] = None,
        verify: VerifyType = None,
        cert: CertType = None,
    ) -> Article:
        html, final_url, headers = self.fetch(url, timeout=timeout, verify=verify, cert=cert)
        return self.parse(html, final_url, headers)


__all__ = ["NewsScraper", "Article"]
