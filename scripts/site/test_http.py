#!/usr/bin/env python3
"""Exercise the shipping Caddy site block against a temporary localhost server."""

import http.client
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "site"


class HTTPContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not shutil.which("caddy"):
            raise RuntimeError("Install Caddy to run the production HTTP contract tests")
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            cls.port = reservation.getsockname()[1]
        cls.log = tempfile.TemporaryFile()
        cls.addClassCleanup(cls.log.close)
        cls.storage = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.storage.cleanup)
        env = {**os.environ, "COMFYWARE_DOMAIN": f"http://127.0.0.1:{cls.port}",
               "COMFYWARE_ROOT": str(SITE),
               "XDG_DATA_HOME": str(Path(cls.storage.name) / "data"),
               "XDG_CONFIG_HOME": str(Path(cls.storage.name) / "config")}
        cls.server = subprocess.Popen(
            ["caddy", "run", "--config", "-", "--adapter", "caddyfile"],
            stdin=subprocess.PIPE, stdout=cls.log, stderr=cls.log, env=env,
        )
        cls.addClassCleanup(cls.stop_server)
        config = "{\n admin off\n}\n" + (ROOT / "scripts/site/Caddyfile").read_text()
        config = config.replace("\troot *", "\tbind 127.0.0.1\n\troot *", 1)
        cls.server.stdin.write(config.encode())
        cls.server.stdin.close()
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                if cls.request("GET", "/")[0] == 200:
                    return
            except OSError:
                pass
            if cls.server.poll() is not None:
                break
            time.sleep(.05)
        cls.log.seek(0)
        raise RuntimeError(f"Caddy failed to start: {cls.log.read().decode()}")

    @classmethod
    def stop_server(cls):
        if cls.server.poll() is None:
            cls.server.terminate()
            try:
                cls.server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                cls.server.kill()
                cls.server.wait(timeout=5)

    @classmethod
    def request(cls, method, path):
        connection = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=3)
        try:
            connection.request(method, path)
            response = connection.getresponse()
            return response.status, dict((key.lower(), value) for key, value in response.getheaders()), response.read()
        finally:
            connection.close()

    def test_routes_deliver_exact_documents(self):
        for route, path in (("/", "index.html"), ("/imvault/", "imvault/index.html"),
                            ("/witmoot/", "witmoot/index.html")):
            with self.subTest(route=route):
                status, headers, body = self.request("GET", route)
                self.assertEqual(status, 200)
                self.assertEqual(body, (SITE / path).read_bytes())
                self.assertIn("text/html", headers["content-type"])
                self.assertEqual(headers["cache-control"], "no-cache")

    def test_assets_and_content_types(self):
        assets = {"/assets/site.css": "text/css", "/assets/theme.js": "text/javascript", "/assets/mark.svg": "image/svg+xml", "/assets/comfy-robot.png": "image/png",
                  "/assets/imvault-gallery.png": "image/png", "/assets/witmoot-board.png": "image/png"}
        for route, mime in assets.items():
            with self.subTest(route=route):
                status, headers, body = self.request("GET", route)
                self.assertEqual(status, 200)
                self.assertIn(mime, headers["content-type"])
                self.assertEqual(body, (SITE / route.lstrip("/")).read_bytes())
                self.assertEqual(headers["cache-control"], "public, max-age=3600")

    def test_directory_redirects(self):
        for route in ("/imvault", "/witmoot"):
            status, headers, _ = self.request("GET", route)
            self.assertEqual(status, 308)
            self.assertEqual(headers["location"], route + "/")

    def test_unknown_routes_preserve_404_status(self):
        for path in ("/missing", "/missing/deep/", "/missing?q=%3Cscript%3E"):
            status, _, body = self.request("GET", path)
            self.assertEqual(status, 404)
            self.assertEqual(body, (SITE / "404.html").read_bytes())

    def test_repository_paths_and_traversal_are_not_served(self):
        for path in ("/.git/config", "/README.md", "/scripts/site/Caddyfile", "/assets/",
                     "/%2e%2e/README.md", "/assets/%2e%2e/%2e%2e/README.md"):
            with self.subTest(path=path):
                status, _, body = self.request("GET", path)
                self.assertEqual(status, 404)
                self.assertEqual(body, (SITE / "404.html").read_bytes())

    def test_query_data_does_not_change_the_document(self):
        status, _, body = self.request("GET", "/?q=%3Cscript%3Ealert(1)%3C/script%3E")
        self.assertEqual(status, 200)
        self.assertEqual(body, (SITE / "index.html").read_bytes())

    def test_head_returns_headers_without_body(self):
        status, headers, body = self.request("HEAD", "/imvault/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["content-type"])
        self.assertEqual(body, b"")

    def test_static_host_rejects_writes(self):
        for method in ("POST", "PUT", "PATCH", "DELETE", "OPTIONS", "TRACE"):
            for path in ("/", "/assets/site.css", "/missing"):
                with self.subTest(method=method, path=path):
                    status, headers, body = self.request(method, path)
                    self.assertEqual(status, 405)
                    self.assertEqual(headers["allow"], "GET, HEAD")
                    self.assertEqual(body, b"Method Not Allowed")

    def test_security_headers(self):
        for path in ("/", "/assets/site.css", "/missing"):
            _, headers, _ = self.request("GET", path)
            self.assertEqual(headers["x-content-type-options"], "nosniff")
            self.assertEqual(headers["referrer-policy"], "strict-origin-when-cross-origin")
            self.assertIn("default-src 'none'", headers["content-security-policy"])
            self.assertIn("script-src 'self'", headers["content-security-policy"])
            self.assertNotIn("unsafe-inline", headers["content-security-policy"])
            self.assertIn("frame-ancestors 'none'", headers["content-security-policy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
