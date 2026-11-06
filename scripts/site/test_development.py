"""New app discovery, truthful status, product boundaries, and regression mutations."""
from pathlib import Path
import shutil
import tempfile
import unittest

from test_content import Document, SITE, development_errors, validate_site


class DevelopmentTests(unittest.TestCase):
    def test_home_and_project_contracts(self):
        for route, relative in (("/", "index.html"), ("/folkweave/", "folkweave/index.html"), ("/tidings/", "tidings/index.html")):
            with self.subTest(route=route):
                self.assertEqual(development_errors(Document((SITE / relative).read_text()), route), [])

    def test_missing_pages_artwork_and_status_fail_the_deploy_gate(self):
        for relative in ("folkweave/index.html", "tidings/index.html", "assets/folkweave-loom.webp", "assets/tidings-town-crier.png"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                (root / relative).unlink()
                self.assertTrue(validate_site(root))

    def test_development_links_and_public_promises_reject_mutations(self):
        for app in ("folkweave", "tidings"):
            original = (SITE / app / "index.html").read_text()
            source = "https://github.com/airencracken/" + app
            mutations = [
                (f'data-development="{app}"', 'data-development="other"'),
                (f'href="{source}"', f'href="{source}/releases/latest"'),
                (f'href="{source}/issues"', 'href="https://example.org/"'),
                ("parental approval controls are not implemented" if app == "folkweave" else "restore with the service stopped", "future work"),
            ]
            for before, after in mutations:
                with self.subTest(app=app, mutation=after):
                    self.assertIn(before, original)
                    self.assertTrue(development_errors(Document(original.replace(before, after)), f"/{app}/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
