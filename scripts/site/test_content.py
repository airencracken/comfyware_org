#!/usr/bin/env python3
"""Validate the public routes, metadata, links, and self-contained static assets."""

import collections
import json
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
          "/songstead/": "songstead/index.html", "/comfylib/": "comfylib/index.html", "/404.html": "404.html",
          **{f"/{app}/docs/": f"{app}/docs/index.html" for app in ("imvault", "witmoot", "songstead")}}
NAV = [("/imvault/", "Imvault"), ("/witmoot/", "Witmoot"), ("/songstead/", "Songstead"), ("/principles/", "Principles"), ("/#sponsor", "Sponsor")]
# Bytes a visitor or social preview crawler downloads for one image.
IMAGE_BUDGET = 200_000
MASCOT_BUDGETS = {"assets/comfy-robot.webp": 45_000, "assets/comfy-robot.png": 100_000}
ICON_BUDGET = 64_000
RELEASE_NAMES = {"imvault": "Imvault", "witmoot": "Witmoot", "songstead": "Songstead", "arise": "Arise", "comfylib": "Comfylib"}
RELEASE_FILE = Path(__file__).with_name("releases.json")
VOID = set("area base br col embed hr img input link meta param source track wbr".split())


class Document(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = collections.defaultdict(list)
        self.ids = []
        self.stack = []
        self.errors = []
        self.nav = None
        self.nav_depth = None
        self.nav_text = None
        self.inline_script = False
        self.links = []
        self.current_link = None
        self.main_text = []
        self.prose = []
        self.feed(text)
        self.close()
        if self.stack:
            self.errors.append(f"Unclosed tags: {self.stack}")

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.tags[tag].append(attrs)
        if tag == "a":
            self.current_link = [attrs, ""]
            self.links.append(self.current_link)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "nav" and attrs.get("class") == "site-nav":
            self.nav = []
            self.nav_depth = len(self.stack) + 1
        elif tag == "a" and self.nav_depth is not None:
            self.nav.append([attrs.get("href"), "", attrs.get("aria-current")])
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag == "nav" and len(self.stack) == self.nav_depth:
            self.nav_depth = None
        if tag == "a":
            self.current_link = None
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"Mismatched closing tag: {tag}")
        else:
            self.stack.pop()

    def handle_data(self, data):
        if "main" in self.stack:
            self.main_text.append(data)
            if self.current_link is None or "data-release" not in self.current_link[0]:
                self.prose.append(data)
        if self.current_link is not None:
            self.current_link[1] += data
        if self.nav and self.nav_depth is not None and self.stack[-1] == "a":
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


def release_versions(path=RELEASE_FILE):
    versions = json.loads(path.read_text())
    if not isinstance(versions, dict) or set(versions) != set(RELEASE_NAMES):
        raise ValueError("Release versions must name exactly the published projects")
    number = r"(?:0|[1-9][0-9]*)"
    for version in versions.values():
        if not isinstance(version, str) or not re.fullmatch(rf"{number}\.{number}\.{number}", version):
            raise ValueError("Release versions must be stable X.Y.Z versions")
    return versions


def release_errors(doc, apps, versions):
    errors = []
    links = [(attrs, text.strip()) for attrs, text in doc.links if "data-release" in attrs]
    if collections.Counter(attrs["data-release"] for attrs, _ in links) != collections.Counter(apps):
        errors.append("Expected one current release link for each app")
    for attrs, text in links:
        app = attrs["data-release"]
        if app not in apps:
            continue
        expected = f"https://github.com/airencracken/{app}/releases/tag/v{versions[app]}"
        if attrs.get("href") != expected or text != f"{RELEASE_NAMES[app]} {versions[app]}":
            errors.append(f"{app}: Release version and link must match the release manifest")
    return errors


def container_errors(doc, route):
    """Keep the published-image installation path visible and app-specific."""
    apps = ("imvault", "witmoot", "songstead") if route == "/" else (route.strip("/").split("/")[0],)
    if route != "/" and route not in tuple(f"/{app}/{suffix}" for app in apps if app in ("imvault", "witmoot", "songstead") for suffix in ("", "docs/")):
        return []
    errors = []
    links = [(attrs, text.strip()) for attrs, text in doc.links if "data-container" in attrs]
    if collections.Counter(attrs["data-container"] for attrs, _ in links) != collections.Counter(apps):
        errors.append("Expected one Docker installation link for each app")
    for attrs, text in links:
        app = attrs["data-container"]
        if (app not in apps or attrs.get("href") != f"https://github.com/airencracken/{app}/blob/master/docs/containers.md"
                or "Docker Compose" not in text):
            errors.append("Docker installation link must name and point to the matching maintained guide")
    if route.endswith("/docs/"):
        app = apps[0]
        if f"https://github.com/airencracken/{app}/pkgs/container/{app}" not in {attrs.get("href") for attrs in doc.tags["a"]}:
            errors.append("Documentation must link to the matching published container package")
    return errors


def editorial_errors(doc, route):
    """Keep product pages brief and operational guides easy to find."""
    errors = []
    app = route.strip("/").split("/")[0]
    links = {attrs.get("href") for attrs in doc.tags["a"]}
    if route == f"/{app}/" and app in ("imvault", "witmoot", "songstead"):
        if len(" ".join(doc.main_text).split()) > 650:
            errors.append("Product copy exceeds the 650-word budget; move details into documentation")
        if re.search(r"\b[0-9]+\.[0-9]+\.[0-9]+\b", " ".join(doc.prose)):
            errors.append("Version-specific prose belongs in release notes")
        for topic in ("install", "backups"):
            if f"/{app}/docs/#{topic}" not in links:
                errors.append(f"Product must link to {topic} documentation")
    if route == f"/{app}/docs/":
        for topic in ("install", "operate", "backups", "upgrades", "help"):
            if topic not in doc.ids or "#" + topic not in links:
                errors.append(f"Documentation must expose the {topic} topic")
        source = f"https://github.com/airencracken/{app}"
        for path in ("/blob/master/docs/releases.md", "/blob/master/docs/deployment.md",
                     "/blob/master/docs/automatic-backups.md", "/releases/latest", "/issues"):
            if source + path not in links:
                errors.append(f"Documentation must link to the maintained guide: {path}")
    return errors



def library_errors(doc, route, versions):
    """Keep the shared library discoverable with an exact Go module pin."""
    links = {attrs.get("href") for attrs in doc.tags["a"]}
    errors = []
    if route == "/" and "/comfylib/" not in links:
        errors.append("Homepage must expose the Comfylib project page")
    if route == "/comfylib/":
        expected = f"go get github.com/airencracken/comfylib@v{versions['comfylib']}"
        commands = [attrs for attrs in doc.tags["code"] if attrs.get("data-module") == "comfylib"]
        if len(commands) != 1 or expected not in " ".join(doc.main_text):
            errors.append("Library installation must pin the published Comfylib module")
        for link in ("https://github.com/airencracken/comfylib", "https://pkg.go.dev/github.com/airencracken/comfylib", "/imvault/", "/witmoot/", "/songstead/"):
            if link not in links:
                errors.append("Library page must expose source, reference and companion apps")
        if any(attrs.get("data-container") for attrs in doc.tags["a"]):
            errors.append("Library page must describe its Go module installation")
    return errors


def validate_site(root):
    errors = []
    versions = release_versions()
    documents = {}
    for route, relative in ROUTES.items():
        path = root / relative
        if not path.is_file():
            errors.append(f"Missing route: {route}")
            continue
        text = path.read_text()
        doc = Document(text)
        documents[route] = doc
        errors.extend(f"{route}: {error}" for error in editorial_errors(doc, route))
        errors.extend(f"{route}: {error}" for error in container_errors(doc, route))
        errors.extend(f"{route}: {error}" for error in library_errors(doc, route, versions))
        apps = list(versions) if route == "/" else [route.strip("/")] if route.strip("/") in versions else []
        errors.extend(f"{route}: {error}" for error in release_errors(doc, apps, versions))
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
        current = next((href for href, _ in NAV if route.startswith(href) and not href.startswith('/#')), None)
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
    def test_all_app_versions_match_their_release_notes(self):
        versions = release_versions()
        for route in ("index.html", "imvault/index.html", "witmoot/index.html", "songstead/index.html", "comfylib/index.html"):
            doc = Document((SITE / route).read_text())
            apps = list(versions) if route == "index.html" else [route.split("/")[0]]
            self.assertEqual(release_errors(doc, apps, versions), [])

    def test_release_link_mutations_are_rejected(self):
        versions = release_versions()
        original = (SITE / "index.html").read_text()
        for app, name in RELEASE_NAMES.items():
            version = versions[app]
            before = f'data-release="{app}" href="https://github.com/airencracken/{app}/releases/tag/v{version}">{name} {version}'
            self.assertIn(before, original)
            other_app = "witmoot" if app == "imvault" else "imvault"
            for after in (
                before.replace(f'data-release="{app}"', f'data-release="{other_app}"'),
                before.replace(f"v{version}", "v99.100.1000"),
                before.replace(f">{name} {version}", f">{name} 99.100.1000"),
                before.replace("https://github.com", "https://example.com"),
                before.replace("data-release", "data-old-release"),
            ):
                with self.subTest(app=app, after=after):
                    self.assertTrue(release_errors(Document(original.replace(before, after, 1)), list(versions), versions))

    def test_release_manifest_schema_and_version_boundaries(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "releases.json"
            for value in (None, [], {}, {"imvault": "1.0.0"}, dict(release_versions(), unknown="1.0.0")):
                path.write_text(json.dumps(value))
                with self.assertRaises(ValueError):
                    release_versions(path)
            for invalid in (None, 1, "1.0", "01.2.3", "1.2.3-beta", "1.2.3\n", "../1.2.3", "<script>"):
                path.write_text(json.dumps(dict(release_versions(), songstead=invalid)))
                with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                    release_versions(path)
            # Exercise stable versions beyond today's particular release numbers.
            for major in range(5):
                for minor in (0, 9, 10, 99):
                    version = f"{major}.{minor}.0"
                    path.write_text(json.dumps(dict(release_versions(), songstead=version)))
                    versions = release_versions(path)
                    doc = Document(f'<a data-release="songstead" href="https://github.com/airencracken/songstead/releases/tag/v{version}">Songstead {version}</a>')
                    self.assertEqual(release_errors(doc, ["songstead"], versions), [])

    def test_product_pages_expose_installation_and_release_routes(self):
        for app in ("imvault", "witmoot", "songstead"):
            with self.subTest(app=app):
                doc = Document((SITE / app / "index.html").read_text())
                links = {a.get("href") for a in doc.tags["a"]}
                origin = f"https://github.com/airencracken/{app}"
                self.assertIn(origin + "/releases/latest", links)
                self.assertIn(origin + "/blob/master/docs/releases.md", links)
                self.assertIn(origin + "/blob/master/docs/deployment.md", links)

    def test_automatic_backups_are_described_for_each_app(self):
        for app in ("songstead", "imvault", "witmoot"):
            content = (SITE / app / "index.html").read_text()
            for phrase in ("verified backups automatically each day", "another machine", "practice restoring", f"/{app}/docs/#backups"):
                with self.subTest(app=app, phrase=phrase):
                    self.assertIn(phrase, content)

    def test_public_site_contract(self):
        self.assertEqual(validate_site(SITE), [])

    def test_no_private_or_build_files_in_public_root(self):
        self.assertEqual({str(p.relative_to(SITE)) for p in SITE.rglob("*") if p.is_file()}, {
            *ROUTES.values(), "assets/site.css", "assets/theme.js", "assets/mark.svg", "assets/comfy-robot.png",
            "assets/comfy-robot.webp", "assets/favicon-64.png", "assets/apple-touch-icon.png", "assets/imvault-gallery.webp",
            "assets/witmoot-board.webp", "assets/imvault-gallery.png", "assets/witmoot-board.png", "assets/songstead-jukebox.png", "assets/songstead-recent.webp", "robots.txt", "sitemap.xml",
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
