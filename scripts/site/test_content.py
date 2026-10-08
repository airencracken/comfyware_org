#!/usr/bin/env python3
"""Validate the public routes, metadata, links, and self-contained static assets."""

import collections
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import struct
import tempfile
import unittest
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET

SITE = Path(__file__).resolve().parents[2] / "site"
ORIGIN = "https://comfyware.org"
ROUTES = {"/": "index.html", "/imvault/": "imvault/index.html",
          "/witmoot/": "witmoot/index.html", "/principles/": "principles/index.html",
          "/songstead/": "songstead/index.html", "/404.html": "404.html"}
NAV = [("/imvault/", "Imvault"), ("/witmoot/", "Witmoot"), ("/songstead/", "Songstead"), ("/principles/", "Principles"), ("/#sponsor", "Sponsor")]
# Bytes a visitor or social preview crawler downloads for one image.
IMAGE_BUDGET = 200_000
MASCOT_BUDGETS = {"assets/comfy-robot.webp": 45_000, "assets/comfy-robot.png": 100_000}
ICON_BUDGET = 64_000
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = collections.defaultdict(list)
        self.ids = []
        self.stack = []
        self.errors = []
        self.nav = None
        self.nav_text = None
        self.inline_script = False
        self.feed(text)
        self.close()
        if self.stack:
            self.errors.append(f"Unclosed tags: {self.stack}")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag].append(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "nav" and attrs.get("class") == "site-nav":
            self.nav = []
        elif tag == "a" and self.nav is not None and "nav" in self.stack:
            self.nav.append([attrs.get("href"), "", attrs.get("aria-current")])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Mismatched closing tag: {tag}")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if self.nav and "nav" in self.stack and self.stack[-1] == "a":
            self.nav[-1][1] += data
        if self.stack and self.stack[-1] == "script" and data.strip():
            self.inline_script = True


def image_size(path):
    """Return (width, height) for the PNG and WebP files the site uses."""
    data = path.read_bytes()[:40]
    if data.startswith(b"\x89PNG"):
        return struct.unpack(">II", data[16:24])
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X":
            return (int.from_bytes(data[24:27], "little") + 1, int.from_bytes(data[27:30], "little") + 1)
        if chunk == b"VP8 ":
            return struct.unpack("<HH", data[26:30])[0] & 0x3FFF, struct.unpack("<HH", data[26:30])[1] & 0x3FFF
        if chunk == b"VP8L":
            bits = int.from_bytes(data[21:25], "little")
            return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    return None


def validate_site(root):
    errors = []
    documents = {}
    for route, relative in ROUTES.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Missing route: {route}")
            continue
        text = path.read_text()
        doc = Document(text)
        documents[route] = doc
        errors.extend(f"{route}: {error}" for error in doc.errors)
        if not text.lower().startswith("<!doctype html>"):
            errors.append(f"{route}: Missing HTML doctype")
        for tag in ("html", "head", "body", "title", "h1", "main"):
            if len(doc.tags[tag]) != 1:
                errors.append(f"{route}: Expected one {tag}")
        if not doc.tags["html"] or doc.tags["html"][0].get("lang") != "en":
            errors.append(f"{route}: Missing language")
        if len(doc.ids) != len(set(doc.ids)):
            errors.append(f"{route}: Duplicate IDs")
        names = {tag.get("name"): tag.get("content") for tag in doc.tags["meta"]}
        for meta in doc.tags["meta"]:
            if meta.get("property") != "og:image":
                continue
            url = urlsplit(meta.get("content", ""))
            path = root / unquote(url.path).lstrip("/")
            if (url.scheme != "https" or url.netloc != "comfyware.org"
                    or not path.resolve().is_relative_to(root.resolve()) or not path.is_file()):
                errors.append(f"{route}: Broken social preview image")
            elif image_size(path) is None or path.stat().st_size > IMAGE_BUDGET:
                errors.append(f"{route}: Oversized or invalid social preview image")
        if not names.get("description") or "width=device-width" not in names.get("viewport", ""):
            errors.append(f"{route}: Missing description or responsive viewport")
        canonical = [tag.get("href") for tag in doc.tags["link"] if tag.get("rel") == "canonical"]
        if route != "/404.html" and canonical != [ORIGIN + route]:
            errors.append(f"{route}: Incorrect canonical URL")
        if route == "/404.html" and names.get("robots") != "noindex":
            errors.append(f"{route}: Error page must be noindex")
        if (doc.tags["script"] != [{"src": "/assets/theme.js"}] or doc.inline_script
                or doc.tags["iframe"] or doc.tags["form"] or doc.tags["base"]):
            errors.append(f"{route}: Unexpected active content")
        if text.find('<script src="/assets/theme.js"></script>') > text.find('rel="stylesheet"'):
            errors.append(f"{route}: Theme must load before the stylesheet")
        icons = [tag for tag in doc.tags["link"] if tag.get("rel") in ("icon", "apple-touch-icon")]
        if icons != [{"rel": "icon", "href": "/assets/favicon-64.png", "type": "image/png", "sizes": "64x64"},
                     {"rel": "apple-touch-icon", "href": "/assets/apple-touch-icon.png"}]:
            errors.append(f"{route}: Missing mascot favicon")
        for icon in icons:
            path = root / icon.get("href", "").lstrip("/")
            if path.is_file() and path.stat().st_size > ICON_BUDGET:
                errors.append(f"{route}: Oversized icon: {icon['href']}")
        current = {"/imvault/": "/imvault/", "/witmoot/": "/witmoot/", "/principles/": "/principles/", "/songstead/": "/songstead/"}.get(route)
        expected_nav = [[href, text, "page" if href == current else None] for href, text in NAV]
        if doc.nav != expected_nav:
            errors.append(f"{route}: Navigation differs from the other pages")
        if doc.tags["select"] != [{"id": "theme"}]:
            errors.append(f"{route}: Missing theme control")
        if [option.get("value") for option in doc.tags["option"]] != ["system", "light", "dark"]:
            errors.append(f"{route}: Invalid theme choices")
        if not any(label.get("class") == "theme-picker" and "hidden" in label for label in doc.tags["label"]):
            errors.append(f"{route}: Theme control must start hidden without JavaScript")
        for tag, elements in doc.tags.items():
            for attrs in elements:
                if any(key.startswith("on") for key in attrs) or "style" in attrs:
                    errors.append(f"{route}: Inline code or styles")
                for ref in attrs.get("aria-labelledby", "").split():
                    if ref not in doc.ids:
                        errors.append(f"{route}: Missing accessible label: {ref}")
        for attrs in doc.tags["img"]:
            if "alt" not in attrs:
                errors.append(f"{route}: Missing image alt text")
            if not all(attrs.get(key, "").isdigit() for key in ("width", "height")):
                errors.append(f"{route}: Missing image dimensions")
            src = attrs.get("src", "")
            path = root / src.lstrip("/")
            if src.startswith("/") and not src.endswith(".svg") and path.is_file():
                dimensions = image_size(path)
                if dimensions is None or tuple(map(str, dimensions)) != (attrs.get("width"), attrs.get("height")):
                    errors.append(f"{route}: Incorrect image dimensions: {src}")
                if path.stat().st_size > IMAGE_BUDGET:
                    errors.append(f"{route}: Oversized image: {src}")
        if not any(a.get("href") == "#main" for a in doc.tags["a"]):
            errors.append(f"{route}: Missing skip link")
        # One way to sponsor: the navigation leads to the home page's sponsor
        # section, which holds the only Ko-fi link.
        kofi = sum(a.get("href") == "https://ko-fi.com/airencracken" for a in doc.tags["a"])
        if kofi != (1 if route == "/" else 0):
            errors.append(f"{route}: Expected the Ko-fi link only in the home page's sponsor section")

    for route, doc in documents.items():
        for tag, attr in (("a", "href"), ("img", "src"), ("link", "href"), ("script", "src")):
            for element in doc.tags[tag]:
                ref = element.get(attr, "")
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    if url.scheme != "https" or not url.netloc:
                        errors.append(f"{route}: Unsafe URL: {ref}")
                    if tag in ("img", "script") or (tag == "link" and element.get("rel") != "canonical"):
                        errors.append(f"{route}: External asset: {ref}")
                    continue
                if not ref or not ref.startswith(("/", "#")):
                    errors.append(f"{route}: URL must be root-relative: {ref}")
                    continue
                target = unquote(url.path) or route
                path = root / ROUTES.get(target, target.lstrip("/"))
                if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
                    errors.append(f"{route}: Broken local URL: {ref}")
                if url.fragment and (target not in documents or unquote(url.fragment) not in documents[target].ids):
                    errors.append(f"{route}: Broken fragment: {ref}")

    for relative, budget in MASCOT_BUDGETS.items():
        path = root / relative
        if not path.is_file() or path.stat().st_size > budget:
            errors.append(f"Mascot exceeds download budget: {relative}")
    css = (root / "assets/site.css").read_text()
    if re.search(r"@import\b|url\s*\(", css, re.I):
        errors.append("CSS must use only the bundled assets and system fonts")
    sitemap = ET.parse(root / "sitemap.xml")
    locations = [node.text for node in sitemap.findall("{*}url/{*}loc")]
    if sorted(locations) != sorted(ORIGIN + route for route in ROUTES if route != "/404.html"):
        errors.append("Sitemap must list each public route exactly once")
    if f"Sitemap: {ORIGIN}/sitemap.xml" not in (root / "robots.txt").read_text():
        errors.append("robots.txt must reference the sitemap")
    return errors


class SiteContractTests(unittest.TestCase):
    def test_product_pages_expose_installation_and_release_routes(self):
        for app in ("imvault", "witmoot", "songstead"):
            with self.subTest(app=app):
                doc = Document((SITE / app / "index.html").read_text())
                links = {a.get("href") for a in doc.tags["a"]}
                origin = f"https://github.com/airencracken/{app}"
                self.assertIn(origin + "/releases/latest", links)
                self.assertIn(origin + "/blob/master/docs/releases.md", links)
                self.assertIn(origin + "/blob/master/docs/deployment.md", links)

    def test_public_site_contract(self):
        self.assertEqual(validate_site(SITE), [])

    def test_no_private_or_build_files_in_public_root(self):
        self.assertEqual({str(p.relative_to(SITE)) for p in SITE.rglob("*") if p.is_file()}, {
            *ROUTES.values(), "assets/site.css", "assets/theme.js", "assets/mark.svg", "assets/comfy-robot.png",
            "assets/comfy-robot.webp", "assets/favicon-64.png", "assets/apple-touch-icon.png", "assets/imvault-gallery.png",
            "assets/witmoot-board.png", "assets/songstead-jukebox.png", "assets/songstead-recent.png", "robots.txt", "sitemap.xml",
        })

    def test_mutations_are_rejected(self):
        mutations = [
            ('href="/imvault/"', 'href="/missing/"', "Broken local URL"),
            ('href="#software"', 'href="#missing"', "Broken fragment"),
            ('id="software"', 'id="main"', "Duplicate IDs"),
            ('</head>', '<script src="/bad.js"></script></head>', "Unexpected active content"),
            ('src="/assets/theme.js"', 'src="https://example.com/theme.js"', "Unexpected active content"),
            ('</script>', 'alert(1)</script>', "Unexpected active content"),
            ('<script src="/assets/theme.js">', '<script defer src="/assets/theme.js">', "Unexpected active content"),
            ('href="/assets/favicon-64.png"', 'href="/assets/mark.svg"', "Missing mascot favicon"),
            ('<a href="/principles/">Principles</a><a href="https://github.com/airencracken/comfyware_org">Source</a></div>',
             '<a href="/principles/">Principles</a><a href="https://github.com/airencracken/comfyware_org">Source</a><a href="https://ko-fi.com/airencracken">Ko-fi</a></div>',
             "Expected the Ko-fi link only"),
            ('<a class="button secondary" href="https://ko-fi.com/airencracken">', '<a class="button secondary" href="/principles/">',
             "Expected the Ko-fi link only"),
            ('href="/assets/favicon-64.png"', 'href="/assets/comfy-robot.png"', "Missing mascot favicon"),
            ('content="https://comfyware.org/assets/comfy-robot.png"', 'content="https://comfyware.org/assets/missing.png"', "Broken social preview image"),
            ('content="https://comfyware.org/assets/comfy-robot.png"', 'content="https://example.com/robot.png"', "Broken social preview image"),
            ('content="https://comfyware.org/assets/comfy-robot.png"', 'content="https://comfyware.org/%2e%2e/README.md"', "Broken social preview image"),
            ('width="680"', 'width="681"', "Incorrect image dimensions"),
            ('<a href="/principles/">Principles</a><a href="/#sponsor">', '<a href="/#sponsor">', "Navigation differs"),
            ('<a href="/witmoot/">Witmoot</a><a href="/songstead/">Songstead</a><a href="/principles/">', '<a href="/witmoot/" aria-current="page">Witmoot</a><a href="/songstead/">Songstead</a><a href="/principles/">', "Navigation differs"),
            ('value="dark"', 'value="unexpected"', "Invalid theme choices"),
            ('class="theme-picker" hidden', 'class="theme-picker"', "Theme control must start hidden"),
            ('<body>', '<body onload="alert(1)">', "Inline code"),
            ('href="https://comfyware.org/"', 'href="https://example.com/"', "Incorrect canonical"),
            ('href="#about"', 'href="javascript:alert(1)"', "Unsafe URL"),
            ('width="1120"', 'width="1"', "Incorrect image dimensions"),
            ('href="#about"', 'href="/%2e%2e/README.md"', "Broken local URL"),
            ('src="/assets/mark.svg"', 'src="https://example.com/tracker.svg"', "External asset"),
        ]
        for old, new, expected in mutations:
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                path = root / "index.html"
                self.assertIn(old, path.read_text())
                path.write_text(path.read_text().replace(old, new, 1))
                self.assertTrue(any(expected in error for error in validate_site(root)))

    def test_mascot_budgets_reject_regressions_at_the_boundary(self):
        for relative, budget in MASCOT_BUDGETS.items():
            with self.subTest(asset=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                path = root / relative
                original = path.read_bytes()
                self.assertEqual(image_size(path), (680, 680))
                for size in (budget, budget + 1):
                    path.write_bytes(original + bytes(size - len(original)))
                    self.assertEqual(any("Mascot exceeds download budget" in error
                                         for error in validate_site(root)), size > budget)


class ImageSizeTests(unittest.TestCase):
    def test_every_webp_layout_is_measured(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "image.webp"
            cases = {
                "VP8X": b"RIFF\0\0\0\0WEBPVP8X" + bytes(8) + (99).to_bytes(3, "little") + (49).to_bytes(3, "little"),
                "VP8 ": b"RIFF\0\0\0\0WEBPVP8 " + bytes(10) + struct.pack("<HH", 100, 50),
                "VP8L": b"RIFF\0\0\0\0WEBPVP8L" + bytes(5) + (99 | (49 << 14)).to_bytes(4, "little"),
            }
            for chunk, data in cases.items():
                with self.subTest(chunk=chunk):
                    path.write_bytes(data + bytes(16))
                    self.assertEqual(tuple(image_size(path)), (100, 50))
            path.write_bytes(b"GIF89a" + bytes(40))
            self.assertIsNone(image_size(path))


if __name__ == "__main__":
    unittest.main(verbosity=2)
