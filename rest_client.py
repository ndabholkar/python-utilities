"""
Simple REST client utility based on the `requests` library with SSL handling.

Features:
- Supports all common HTTP methods: GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS.
- Allows query parameters (`params`) and JSON payloads (`json_body`).
- Merges default headers with per-request headers.
- SSL: configurable certificate verification (`verify`) and client certificates (`cert`).
- Returns parsed JSON (`dict`/`list`) when response is JSON; returns `None` when response is empty or non‑JSON.
- Raises `requests.exceptions.HTTPError` for non‑2xx responses by default (configurable per call).
"""

from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union

import requests
from requests.exceptions import HTTPError as RequestsHTTPError


JSONType = Any  # Parsed JSON object: dict, list, str, int, float, bool, or None


def _is_json_content_type(content_type: Optional[str]) -> bool:
    if not content_type:
        return False
    # e.g., "application/json; charset=utf-8" or "+json" types
    ctype = content_type.lower()
    return "application/json" in ctype or "+json" in ctype


def _join_url(base_url: Optional[str], url: str) -> str:
    if not base_url:
        return url
    # urljoin handles absolute `url` by replacing base
    return urllib.parse.urljoin(base_url if base_url.endswith('/') else base_url + '/', url)


def _merge_query(url: str, params: Optional[Mapping[str, Any]]) -> str:
    if not params:
        return url
    parsed = urllib.parse.urlparse(url)
    original_qs = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    # Convert provided params into list of tuples while preserving multiple values
    new_qs_items = []
    for k, v in params.items():
        if isinstance(v, (list, tuple)):
            for item in v:
                new_qs_items.append((k, "" if item is None else str(item)))
        else:
            new_qs_items.append((k, "" if v is None else str(v)))
    merged_qs = original_qs + new_qs_items
    encoded_qs = urllib.parse.urlencode(merged_qs, doseq=True)
    rebuilt = parsed._replace(query=encoded_qs)
    return urllib.parse.urlunparse(rebuilt)


@dataclass
class RestClient:
    base_url: Optional[str] = None
    default_headers: Dict[str, str] = field(default_factory=dict)
    timeout: Optional[float] = 30.0
    # SSL controls
    verify: Optional[Union[bool, str]] = True  # True/False or path to CA bundle
    cert: Optional[Union[str, Tuple[str, str]]] = None  # client cert file or (cert, key)

    # Internal session (connection pooling)
    _session: requests.Session = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._session = requests.Session()

    def _build_headers(self, headers: Optional[Mapping[str, str]], has_json_body: bool) -> Dict[str, str]:
        merged: Dict[str, str] = {}
        merged.update(self.default_headers or {})
        if has_json_body:
            merged.setdefault("Content-Type", "application/json; charset=utf-8")
        # Be explicit about expecting JSON by default
        merged.setdefault("Accept", "application/json")
        if headers:
            merged.update(headers)
        return merged

    def request(
        self,
        method: str,
        url: str,
        *,
        params: Optional[Mapping[str, Any]] = None,
        json_body: Optional[Any] = None,
        headers: Optional[Mapping[str, str]] = None,
        timeout: Optional[float] = None,
        raise_for_status: bool = True,
        verify: Optional[Union[bool, str]] = None,
        cert: Optional[Union[str, Tuple[str, str]]] = None,
    ) -> Optional[JSONType]:
        """
        Execute an HTTP request.

        Returns:
            Parsed JSON object when response has JSON content; None when response
            is empty (e.g., 204) or not JSON.
        Raises:
            requests.exceptions.HTTPError for non-2xx codes when `raise_for_status` is True.
        """
        method_upper = method.upper()
        full_url = _join_url(self.base_url, url)

        has_json_body = json_body is not None and method_upper not in {"GET", "HEAD", "OPTIONS"}
        req_headers = self._build_headers(headers, has_json_body=has_json_body)

        # Timeout precedence: per-call > client default > urllib default
        effective_timeout = timeout if timeout is not None else self.timeout
        effective_verify = self.verify if verify is None else verify
        effective_cert = self.cert if cert is None else cert

        try:
            # Only send a JSON body for methods that support a body (keep behavior consistent)
            json_arg = json_body if has_json_body else None

            resp = self._session.request(
                method=method_upper,
                url=full_url,
                params=dict(params) if params else None,
                json=json_arg,
                headers=req_headers,
                timeout=effective_timeout,
                verify=effective_verify,  # SSL verification control
                cert=effective_cert,      # client certificate
                allow_redirects=True,
            )

            if raise_for_status:
                resp.raise_for_status()
            else:
                if resp.status_code >= 400:
                    return None

            # For HEAD, always return None
            if method_upper == "HEAD":
                return None

            content_type = resp.headers.get("Content-Type")

            # Empty or no-content
            if resp.status_code in {204, 205}:
                return None
            if not resp.content:
                return None

            if _is_json_content_type(content_type):
                try:
                    return resp.json()
                except Exception:
                    return None

            # Not a JSON content-type: return None per requirements
            return None
        except RequestsHTTPError:
            if raise_for_status:
                raise
            return None

    # Convenience methods
    def get(self, url: str, *, params: Optional[Mapping[str, Any]] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("GET", url, params=params, headers=headers, timeout=timeout)

    def post(self, url: str, *, params: Optional[Mapping[str, Any]] = None, json_body: Optional[Any] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("POST", url, params=params, json_body=json_body, headers=headers, timeout=timeout)

    def put(self, url: str, *, params: Optional[Mapping[str, Any]] = None, json_body: Optional[Any] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("PUT", url, params=params, json_body=json_body, headers=headers, timeout=timeout)

    def patch(self, url: str, *, params: Optional[Mapping[str, Any]] = None, json_body: Optional[Any] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("PATCH", url, params=params, json_body=json_body, headers=headers, timeout=timeout)

    def delete(self, url: str, *, params: Optional[Mapping[str, Any]] = None, json_body: Optional[Any] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("DELETE", url, params=params, json_body=json_body, headers=headers, timeout=timeout)

    def head(self, url: str, *, params: Optional[Mapping[str, Any]] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("HEAD", url, params=params, headers=headers, timeout=timeout)

    def options(self, url: str, *, params: Optional[Mapping[str, Any]] = None, headers: Optional[Mapping[str, str]] = None, timeout: Optional[float] = None) -> Optional[JSONType]:
        return self.request("OPTIONS", url, params=params, headers=headers, timeout=timeout)


def _detect_charset(content_type: Optional[str]) -> str:
    if not content_type:
        return "utf-8"
    # parse content-type for charset
    parts = [p.strip() for p in content_type.split(';')]
    for p in parts[1:]:
        if p.lower().startswith("charset="):
            return p.split("=", 1)[1].strip() or "utf-8"
    return "utf-8"
