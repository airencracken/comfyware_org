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
          "/witmoot/": "witmoot/index.html", "/404.html": "404.html"}
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = collections.defaultdict(list)
        self.ids = []
        self.stack = []
        self.errors = []
        self.feed(text)
        self.close()
        if self.stack:
            self.errors.append(f"Unclosed tags: {self.stack}")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag].append(attrs)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Mismatched closing tag: {tag}")
        else:
            self.stack.pop()


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
        if not names.get("description") or "width=device-width" not in names.get("viewport", ""):
            errors.append(f"{route}: Missing description or responsive viewport")
        canonical = [tag.get("href") for tag in doc.tags["link"] if tag.get("rel") == "canonical"]
        if route != "/404.html" and canonical != [ORIGIN + route]:
            errors.append(f"{route}: Incorrect canonical URL")
        if route == "/404.html" and names.get("robots") != "noindex":
            errors.append(f"{route}: Error page must be noindex")
        if doc.tags["script"] or doc.tags["iframe"] or doc.tags["form"] or doc.tags["base"]:
            errors.append(f"{route}: Unexpected active content")
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
            if src.endswith(".png") and (root / src.lstrip("/")).is_file():
                dimensions = struct.unpack(">II", (root / src.lstrip("/")).read_bytes()[16:24])
                if tuple(map(str, dimensions)) != (attrs.get("width"), attrs.get("height")):
                    errors.append(f"{route}: Incorrect image dimensions: {src}")
        if not any(a.get("href") == "#main" for a in doc.tags["a"]):
            errors.append(f"{route}: Missing skip link")
        if not any(a.get("href") == "https://ko-fi.com/airencracken" for a in doc.tags["a"]):
            errors.append(f"{route}: Missing support link")

    for route, doc in documents.items():
        for tag, attr in (("a", "href"), ("img", "src"), ("link", "href")):
            for element in doc.tags[tag]:
                ref = element.get(attr, "")
                url = urlsplit(ref)
                if url.scheme or url.netloc:
                    if url.scheme != "https" or not url.netloc:
                        errors.append(f"{route}: Unsafe URL: {ref}")
                    if tag == "img" or (tag == "link" and element.get("rel") != "canonical"):
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
    def test_public_site_contract(self):
        self.assertEqual(validate_site(SITE), [])

    def test_no_private_or_build_files_in_public_root(self):
        self.assertEqual({str(p.relative_to(SITE)) for p in SITE.rglob("*") if p.is_file()}, {
            *ROUTES.values(), "assets/site.css", "assets/mark.svg", "assets/comfy-bear.png", "assets/imvault-gallery.png",
            "assets/witmoot-board.png", "robots.txt", "sitemap.xml",
        })

    def test_mutations_are_rejected(self):
        mutations = [
            ('href="/imvault/"', 'href="/missing/"', "Broken local URL"),
            ('href="#software"', 'href="#missing"', "Broken fragment"),
            ('id="software"', 'id="main"', "Duplicate IDs"),
            ('</head>', '<script src="/bad.js"></script></head>', "Unexpected active content"),
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
