"""Songstead announcement contracts and deliberate regression checks."""
from pathlib import Path
import shutil
import tempfile
import unittest

from test_content import Document, SITE, validate_site


class SongsteadTests(unittest.TestCase):
    def test_project_is_discoverable_with_honest_release_preparation(self):
        home = (SITE / "index.html").read_text()
        product = (SITE / "songstead/index.html").read_text()
        self.assertIn('href="/songstead/"', home)
        self.assertIn("0.1.0", home)
        self.assertIn("0.1.0", product)
        self.assertIn("AGPL-3.0-or-later", product)
        self.assertIn("master", product)
        self.assertIn("no streaming account or playback tracking", product)
        self.assertIn("a gift, never an assignment", product)
        self.assertIn("when the repository and release are available", product)
        self.assertIn("does not host or stream music", product)
        self.assertNotIn("/songstead/releases", product)
        self.assertNotIn("/songstead/blob/master", product)
        document = Document(product)
        self.assertEqual([entry for entry in document.nav if entry[2] == "page"],
                         [["/songstead/", "Songstead", "page"]])

    def test_missing_route_and_artwork_fail_validation(self):
        for path in ("songstead/index.html", "assets/songstead-jukebox.png"):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                (root / path).unlink()
                self.assertTrue(validate_site(root))

    def test_malformed_canonical_and_injected_content_are_rejected(self):
        for old, new in [('https://comfyware.org/songstead/', 'https://example.org/songstead/'),
                         ('<body>', '<body onload="alert(1)">')]:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                page = root / "songstead/index.html"
                page.write_text(page.read_text().replace(old, new, 1))
                self.assertTrue(validate_site(root))


if __name__ == "__main__":
    unittest.main(verbosity=2)
