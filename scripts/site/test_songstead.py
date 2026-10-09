"""Songstead announcement contracts and deliberate regression checks."""
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from test_content import Document, SITE, validate_site


class SongsteadTests(unittest.TestCase):
    def test_privacy_questions_explain_audiences_and_deliberate_participation(self):
        product = (SITE / "songstead/index.html").read_text()
        for phrase in ("Who can see what I share?", "There is no anonymous feed.",
                       "current members of its group", "Does Recent fill my shelf?",
                       "Opening a recommendation changes nothing.",
                       "when you choose to organize it or comment on it",
                       "Can my friends see my listening notes?",
                       "Comments are conversation with the recommendation's audience.",
                       "You choose where to post in Witmoot."):
            self.assertIn(phrase, product)
        self.assertEqual(product.count("<details>"), 4)
        self.assertEqual(product.count("<summary>"), 4)

    def test_released_companion_album_discussions_preserve_privacy(self):
        album=(SITE / "imvault/index.html").read_text()
        board=(SITE / "witmoot/index.html").read_text()
        self.assertIn("Imvault 0.16.2", album)
        self.assertIn("Witmoot 0.14.2", board)
        for page in (album, board):
            self.assertNotIn("next prepared release", page)
            self.assertIn("Private albums" if page == album else "private albums", page)
        self.assertIn("Threads are never created automatically",album)
        self.assertIn("Choose a board or an existing topic",board)
        self.assertIn("on request",board)

    def test_released_project_exposes_source_downloads_and_installation(self):
        home = (SITE / "index.html").read_text()
        product = (SITE / "songstead/index.html").read_text()
        self.assertIn('href="/songstead/"', home)
        self.assertIn("0.5.0", home)
        self.assertIn("0.5.0", product)
        self.assertIn("AGPL-3.0-or-later", product)
        self.assertIn("master", product)
        self.assertIn("optional Bubblewrap support", product)
        self.assertIn('href="https://github.com/airencracken/songstead/blob/master/docs/sandbox.md"', product)
        self.assertIn("no streaming account or playback tracking", product)
        self.assertIn("a gift, never an assignment", product)
        self.assertNotIn("in preparation", product)
        self.assertIn("does not host or stream music", product)
        self.assertIn("Recent shows what people shared with everyone here", product)
        self.assertIn("Private recommendations stay out", product)
        self.assertIn("Your shelf", product)
        self.assertNotIn("inbox", product.lower())
        self.assertIn('href="https://github.com/airencracken/songstead"', product)
        self.assertIn('href="https://github.com/airencracken/songstead/releases/latest"', product)
        self.assertIn('href="https://github.com/airencracken/songstead/blob/master/docs/releases.md"', product)
        self.assertIn('href="https://github.com/airencracken/songstead/blob/master/docs/deployment.md"', product)
        self.assertNotIn("in preparation", home)
        document = Document(product)
        self.assertEqual([entry for entry in document.nav if entry[2] == "page"],
                         [["/songstead/", "Songstead", "page"]])

    def test_administration_and_invitation_copy_matches_available_features(self):
        product = (SITE / "songstead/index.html").read_text()
        for text in ("invitation-only by default", "expiry and use limits", "Witmoot addresses", "one-hour recovery links", "same boundaries around private recommendations", "docs/administration.md", "Discussion location: Songstead, Witmoot or Both", "without a Witmoot account", "No API key is needed", "earlier local comments remain readable"):
            self.assertIn(text, product)

    def test_discovery_copy_matches_the_available_controls(self):
        product = (SITE / "songstead/index.html").read_text()
        for text in ("freeform genre and tags", "privately exclude genres or tags", "Exclusions take priority.", "List or Tiles", "cached locally", "confirmation beside the form", "descriptions on a private send stay inside that send", "Open Your settings", "compact genre and tag pickers", "both include thumbnails", "extra dropdowns stay under More filters", "animated GIF profile picture", "reduced-motion preferences", "thumbnail before you share", "general instance card"):
            self.assertIn(text, product)
        capture = (SITE.parent / "scripts/site/capture-songstead.mjs").read_text()
        self.assertIn("layout=tiles", capture)
        self.assertIn(".artwork-placeholder", capture)
        self.assertIn("media_artwork", capture)

    def test_real_screenshot_is_linked_with_correct_dimensions(self):
        for path in ("index.html", "songstead/index.html"):
            document = Document((SITE / path).read_text())
            screenshots = [tag for tag in document.tags["img"] if tag.get("src") == "/assets/songstead-recent.png"]
            self.assertEqual(len(screenshots), 1)
            self.assertEqual((screenshots[0]["width"], screenshots[0]["height"]), ("1280", "1228"))
            self.assertIn("recommendations", screenshots[0]["alt"])
            self.assertFalse(any(tag.get("src") == "/assets/songstead-jukebox.png" for tag in document.tags["img"]))
        product = (SITE / "songstead/index.html").read_text()
        self.assertIn('class="screenshot"', product)
        self.assertIn('href="/assets/songstead-recent.png"', product)
        self.assertIn("fictional music, local sample artwork and demo accounts", product)

    def test_wrong_screenshot_dimensions_fail_validation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            shutil.copytree(SITE, root)
            page = root / "songstead/index.html"
            page.write_text(page.read_text().replace('height="1228"', 'height="480"'))
            self.assertTrue(validate_site(root))

    def test_browser_status_check_matches_visible_release_copy(self):
        browser=(SITE.parent / "scripts/site/browser.mjs").read_text()
        matches=re.findall(r"getByText\('([^']*Songstead[^']*\d+\.\d+\.\d+[^']*)'",browser)
        self.assertEqual(len(matches),1)
        self.assertIn(matches[0],(SITE / "songstead/index.html").read_text())

    def test_missing_route_and_artwork_fail_validation(self):
        for path in ("songstead/index.html", "assets/songstead-jukebox.png", "assets/songstead-recent.png"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                (root / path).unlink()
                self.assertTrue(validate_site(root))

    def test_malformed_canonical_and_injected_content_are_rejected(self):
        for old, new in [('https://comfyware.org/songstead/', 'https://example.org/songstead/'),
                         ('<body', '<body onload="alert(1)"')]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                page = root / "songstead/index.html"
                original = page.read_text()
                mutated = original.replace(old, new, 1)
                self.assertNotEqual(original, mutated, "Mutation did not apply")
                page.write_text(mutated)
                self.assertTrue(validate_site(root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
