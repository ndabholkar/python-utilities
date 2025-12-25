import json
import threading
import time
import unittest
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from python_utilities import RestClient
import types


class _DummyResponse:
    def __init__(self, status_code=200, headers=None, content=b"{\"ok\": true}"):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/json; charset=utf-8"}
        self._content = content

    @property
    def content(self):
        return self._content

    def json(self):
        return json.loads(self._content.decode("utf-8"))

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


class _Handler(BaseHTTPRequestHandler):
    server_version = "TestHTTP/1.0"

    def _send_json(self, obj, status=200):
        payload = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _send_text(self, text, status=200):
        payload = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return None
        data = self.rfile.read(length)
        try:
            return json.loads(data.decode("utf-8"))
        except Exception:
            return None

    def do_GET(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/error":
            self._send_json({"error": True}, status=HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/text":
            self._send_text("ok", status=200)
            return
        resp = {
            "path": parsed.path,
            "query": parse_qs(parsed.query),
        }
        self._send_json(resp)

    def do_POST(self):  # noqa: N802
        body = self._read_json_body()
        self._send_json({"method": "POST", "json": body})

    def do_PUT(self):  # noqa: N802
        body = self._read_json_body()
        self._send_json({"method": "PUT", "json": body})

    def do_PATCH(self):  # noqa: N802
        body = self._read_json_body()
        self._send_json({"method": "PATCH", "json": body})

    def do_DELETE(self):  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/nocontent":
            self.send_response(HTTPStatus.NO_CONTENT)
            self.end_headers()
            return
        body = self._read_json_body()
        self._send_json({"method": "DELETE", "json": body})

    def do_HEAD(self):  # noqa: N802
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()

    def do_OPTIONS(self):  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self.send_header("Allow", "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS")
        self.end_headers()

    def log_message(self, format, *args):  # silence server logs in tests
        pass


class RestClientTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = HTTPServer(("127.0.0.1", 0), _Handler)
        cls.host, cls.port = cls.httpd.server_address
        cls.base_url = f"http://{cls.host}:{cls.port}"
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        # Small sleep to ensure server is ready
        time.sleep(0.05)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.thread.join(timeout=2)
        cls.httpd.server_close()

    def setUp(self):
        self.client = RestClient(base_url=self.base_url)

    def test_get_with_query_params_returns_json(self):
        res = self.client.get("/foo", params={"a": 1, "b": ["x", "y"]})
        self.assertIsInstance(res, dict)
        self.assertEqual(res["path"], "/foo")
        # parse_qs returns values as lists of strings
        self.assertEqual(res["query"], {"a": ["1"], "b": ["x", "y"]})

    def test_post_put_patch_with_json(self):
        payload = {"x": 1}
        res_post = self.client.post("/echo", json_body=payload)
        self.assertEqual(res_post, {"method": "POST", "json": payload})
        res_put = self.client.put("/echo", json_body=payload)
        self.assertEqual(res_put, {"method": "PUT", "json": payload})
        res_patch = self.client.patch("/echo", json_body=payload)
        self.assertEqual(res_patch, {"method": "PATCH", "json": payload})

    def test_delete_with_json_and_204(self):
        res = self.client.delete("/nocontent", json_body={"a": 2})
        self.assertIsNone(res)

    def test_head_returns_none(self):
        res = self.client.head("/anything")
        self.assertIsNone(res)

    def test_options_returns_none(self):
        res = self.client.options("/anything")
        self.assertIsNone(res)

    def test_non_json_response_returns_none(self):
        res = self.client.get("/text")
        self.assertIsNone(res)

    def test_http_error_raises_by_default(self):
        with self.assertRaises(Exception):
            self.client.get("/error")

    def test_http_error_no_raise_returns_none(self):
        res = self.client.request("GET", "/error", raise_for_status=False)
        self.assertIsNone(res)


class RestClientSSLTest(unittest.TestCase):
    def setUp(self):
        self.client = RestClient(base_url="https://api.example.com", verify=False, cert=("cert.pem", "key.pem"))

        # Monkeypatch the session.request to capture kwargs and avoid real network
        self.captured = {}

        def fake_request(**kwargs):
            # requests.Session.request signature includes 'method' and 'url' as positional
            self.captured = kwargs
            return _DummyResponse(status_code=200)

        # Bind as method compatible with Session.request(method, url, **kwargs)
        def fake_request_bound(_self, method, url, **kwargs):
            self.captured = {**kwargs, "method": method, "url": url}
            return _DummyResponse(status_code=200)

        self.client._session.request = types.MethodType(fake_request_bound, self.client._session)

    def test_client_level_ssl_settings_are_used(self):
        self.client.get("/v1/ping", params={"a": 1})
        self.assertEqual(self.captured.get("verify"), False)
        self.assertEqual(self.captured.get("cert"), ("cert.pem", "key.pem"))

    def test_per_call_ssl_override(self):
        self.client.request("GET", "/v1/ping", verify="/path/ca.pem", cert="client.pem")
        self.assertEqual(self.captured.get("verify"), "/path/ca.pem")
        self.assertEqual(self.captured.get("cert"), "client.pem")

    def test_json_body_and_headers(self):
        payload = {"x": 1}
        self.client.post("/v1/echo", json_body=payload)
        # requests passes JSON payload under 'json'
        self.assertEqual(self.captured.get("json"), payload)


if __name__ == "__main__":
    unittest.main(verbosity=2)
