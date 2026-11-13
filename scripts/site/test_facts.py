"""Keep shared facts identical across pages: packaging, Go, demos, links and app lists.

facts.json is the single record for facts that more than one page repeats. The
site has no build step, so these checks hold every page to it instead.
"""
import json
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from test_content import ROUTES, SITE

FACTS_FILE = Path(__file__).with_name("facts.json")
APPS = ("imvault", "witmoot", "songstead", "folkweave", "tidings")
NAMES = {app: app.capitalize() for app in APPS}
FORMAT_WORDS = {"docker": "Docker images", "binaries": "Linux binaries",
                "debian": "Debian packages", "gentoo": "a Gentoo overlay"}
BACK_TEXT = {"/#software": "All our software", "/#workshop-heading": "All our software", "/#about": "Back to Comfyware",
             **{f"/{app}/": f"Back to {NAMES[app]}" for app in APPS}}


def load_facts(path=FACTS_FILE):
    facts = json.loads(path.read_text())
    if not isinstance(facts, dict) or set(facts) != {"go", "demos", "formats"}:
        raise ValueError("facts.json must hold go, demos and formats")
    if not isinstance(facts["go"], str) or not re.fullmatch(r"1\.[0-9]+\.[0-9]+", facts["go"]):
        raise ValueError("go must be an exact 1.X.Y toolchain version")
    for key in ("demos", "formats"):
        if not isinstance(facts[key], dict) or list(facts[key]) != list(APPS):
            raise ValueError(f"{key} must list the five apps in the family's order")
    for app, anchor in facts["demos"].items():
        if not isinstance(anchor, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", anchor):
            raise ValueError(f"{app}: demo anchor must be a README heading slug")
    for app, formats in facts["formats"].items():
        if (not isinstance(formats, list) or not formats or len(set(formats)) != len(formats)
                or not set(formats) <= set(FORMAT_WORDS) or [f for f in FORMAT_WORDS if f in formats] != formats):
            raise ValueError(f"{app}: formats must be known, unique and in the standard order")
    return facts


def format_phrase(formats):
    words = [FORMAT_WORDS[name] for name in formats]
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + (", and " if len(words) > 2 else " and ") + words[-1]


def product_note(formats):
    return "Self-hosted · Open source · " + format_phrase(formats)


class Page(HTMLParser):
    """Collect the elements these checks read, with their text."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.elements = []
        self.open = []
        self.footer = 0
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "footer":
            self.footer += 1
        element = {"tag": tag, "attrs": attrs, "text": "", "children": [], "footer": self.footer > 0}
        for parent in self.open:
            parent["children"].append(element)
        self.elements.append(element)
        if tag not in ("img", "br", "meta", "link", "input"):
            self.open.append(element)

    def handle_endtag(self, tag):
        if tag == "footer":
            self.footer -= 1
        for index in range(len(self.open) - 1, -1, -1):
            if self.open[index]["tag"] == tag:
                del self.open[index:]
                break

    def handle_data(self, data):
        for element in self.open:
            element["text"] += data

    def find(self, tag=None, cls=None, **attrs):
        return [e for e in self.elements if (tag is None or e["tag"] == tag)
                and (cls is None or cls in e["attrs"].get("class", "").split())
                and all(e["attrs"].get(k) == v for k, v in attrs.items())]


def text_of(element):
    return " ".join(element["text"].split())


def packaging_errors(page, app, facts):
    errors = []
    notes = page.find("p", "product-note")
    if [text_of(n) for n in notes] != [product_note(facts["formats"][app])]:
        errors.append(f"{app}: product note must read '{product_note(facts['formats'][app])}'")
    guide = [a for a in page.find("a") if a["attrs"].get("href") == f"https://github.com/airencracken/{app}/blob/master/docs/releases.md"]
    debian = "debian" in facts["formats"][app]
    if not guide:
        errors.append(f"{app}: product page must link the binary installation guide")
    for link in guide:
        if ("Debian" in text_of(link)) != debian:
            errors.append(f"{app}: installation guide link must {'mention' if debian else 'not mention'} Debian")
    return errors


def go_errors(text, facts):
    versions = set(re.findall(r"\bGo (1\.[0-9]+(?:\.[0-9]+)?)", re.sub(r"<[^>]+>", " ", text)))
    return [f"Go requirement must read Go {facts['go']}, found Go {v}" for v in sorted(versions - {facts["go"]})]


def back_link_errors(page, route):
    links = page.find("a", "back-link")
    if route in ("/", "/404.html"):
        return ["Home and error pages need no back link"] if links else []
    if len(links) != 1:
        return ["Expected one back link"]
    link = links[0]
    arrow = [c for c in link["children"] if c["tag"] == "span" and c["attrs"].get("aria-hidden") == "true"]
    errors = []
    if len(arrow) != 1 or text_of(arrow[0]) != "←" or not link["text"].startswith("←"):
        errors.append("Back link must start with a hidden ← arrow")
    expected = BACK_TEXT.get(link["attrs"].get("href"))
    if expected is None or text_of(link) != "← " + expected:
        errors.append(f"Back link text must be '{expected}'")
    return errors


def demo_errors(page, app, facts):
    items = page.find("li", id="demo")
    if len(items) != 1:
        return [f"{app}: docs need one #demo item"]
    hrefs = [c["attrs"].get("href") for c in items[0]["children"] if c["tag"] == "a"]
    if hrefs != [f"https://github.com/airencracken/{app}#{facts['demos'][app]}"]:
        return [f"{app}: #demo must link the README's demo section"]
    if f"Go {facts['go']}" not in text_of(items[0]):
        return [f"{app}: #demo must state the Go requirement"]
    return []


def footer_current_errors(page, route):
    return [f"Footer marks {a['attrs'].get('href')} as current on {route}" for a in page.find("a")
            if a["footer"] and a["attrs"].get("aria-current") and a["attrs"].get("href") != route]


def app_list_errors(text):
    """A written list of three or more apps should name all five."""
    errors = []
    plain = " ".join(re.sub(r"<[^>]+>", " ", text).split())
    name = "(?:" + "|".join(NAMES.values()) + ")(?:’s|'s)?"
    for match in re.finditer(rf"{name}(?:, {name})+,? (?:and|or) {name}", plain):
        named = [app for app in APPS if NAMES[app] in match[0]]
        if len(named) != len(APPS):
            errors.append("Family list names only " + ", ".join(NAMES[a] for a in named))
    return errors


def principle_errors(page):
    for block in page.find("div"):
        number = [c for c in block["children"] if c["attrs"].get("class") == "principle-number"]
        if number and text_of(number[0]) == "06":
            named = [app for app in APPS if NAMES[app] in text_of(block)]
            if named and len(named) != len(APPS):
                return ["Principle 06 must name all five apps or none"]
            return []
    return ["Homepage is missing principle 06"]


def site_errors(root, facts):
    errors = []
    for route, relative in ROUTES.items():
        text = (root / relative).read_text()
        page = Page(text)
        errors += [f"{route}: {e}" for e in back_link_errors(page, route)]
        errors += [f"{route}: {e}" for e in go_errors(text, facts)]
        errors += [f"{route}: {e}" for e in footer_current_errors(page, route)]
        errors += [f"{route}: {e}" for e in app_list_errors(text)]
        app = route.strip("/").split("/")[0]
        if route == f"/{app}/" and app in APPS:
            errors += [f"{route}: {e}" for e in packaging_errors(page, app, facts)]
        if route == f"/{app}/docs/":
            errors += [f"{route}: {e}" for e in demo_errors(page, app, facts)]
        if route == "/":
            errors += [f"{route}: {e}" for e in principle_errors(page)]
    return errors


class FactTests(unittest.TestCase):
    def test_site_agrees_with_facts(self):
        self.assertEqual(site_errors(SITE, load_facts()), [])

    def test_format_phrases(self):
        self.assertEqual(format_phrase(["docker"]), "Docker images")
        self.assertEqual(format_phrase(["docker", "gentoo"]), "Docker images and a Gentoo overlay")
        self.assertEqual(format_phrase(["docker", "binaries", "gentoo"]),
                         "Docker images, Linux binaries, and a Gentoo overlay")

    def test_facts_schema_rejects_bad_values(self):
        original = json.loads(FACTS_FILE.read_text())
        cases = [None, [], {}, dict(original, extra=1), dict(original, go="1.26"), dict(original, go="go1.26.11"),
                 dict(original, go=126), dict(original, demos={}),
                 dict(original, demos=dict(original["demos"], imvault="../x")),
                 dict(original, demos=dict(original["demos"], imvault="Come On In")),
                 dict(original, formats=dict(reversed(list(original["formats"].items())))),
                 dict(original, formats=dict(original["formats"], songstead=[])),
                 dict(original, formats=dict(original["formats"], songstead=["rpm"])),
                 dict(original, formats=dict(original["formats"], songstead=["gentoo", "docker"])),
                 dict(original, formats=dict(original["formats"], songstead=["docker", "docker"]))]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "facts.json"
            for value in cases:
                with self.subTest(value=value):
                    path.write_text(json.dumps(value))
                    with self.assertRaises((ValueError, TypeError, AttributeError)):
                        load_facts(path)

    def test_page_mutations_are_rejected(self):
        facts = load_facts()
        mutations = [
            ("songstead/index.html", "Linux binaries, and a Gentoo overlay", "Linux binaries, and Gentoo packaging", "product note"),
            ("songstead/index.html", "binary and source guide", "binary and Debian package guide", "not mention Debian"),
            ("imvault/index.html", "Debian packages, and a Gentoo overlay", "and a Gentoo overlay", "product note"),
            ("comfylib/index.html", "Go 1.26.11", "Go 1.26", "Go requirement"),
            ("imvault/index.html", '<span aria-hidden="true">←</span> All our software', "All our software", "hidden ← arrow"),
            ("comfylib/index.html", "</span> All our software", "</span> Back to Comfyware", "Back link text"),
            ("tidings/docs/index.html", 'id="demo"', 'id="try"', "#demo item"),
            ("tidings/docs/index.html", "tidings#try-the-demo", "tidings#readme", "README's demo section"),
            ("index.html", "In Imvault, Witmoot, Songstead, Folkweave, and Tidings, owners", "In Imvault, owners", "Principle 06"),
            ("index.html", "Hosts and members decide", "Imvault, Witmoot, and Songstead hosts decide", "Family list"),
            ("comfylib/index.html", '<a href="https://github.com/airencracken/comfyware_org">Source</a>',
             '<a href="https://github.com/airencracken/comfyware_org" aria-current="page">Source</a>', "Footer marks"),
        ]
        for relative, before, after, expected in mutations:
            with self.subTest(expected=expected, page=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                path = root / relative
                original = path.read_text()
                self.assertIn(before, original)
                path.write_text(original.replace(before, after, 1))
                self.assertTrue(any(expected in error for error in site_errors(root, facts)), site_errors(root, facts))


if __name__ == "__main__":
    unittest.main(verbosity=2)
