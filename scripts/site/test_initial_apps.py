"""Initial app discovery, product boundaries, and regression mutations."""
from pathlib import Path
import shutil
import tempfile
import unittest

from test_content import Document, SITE, initial_app_errors, project_screenshot_errors, validate_site


class InitialAppTests(unittest.TestCase):
    def test_project_boundaries(self):
        for route, relative in (("/folkweave/", "folkweave/index.html"), ("/tidings/", "tidings/index.html")):
            with self.subTest(route=route):
                self.assertEqual(initial_app_errors(Document((SITE / relative).read_text()), route), [])

    def test_missing_pages_and_artwork_fail_the_deploy_gate(self):
        for relative in ("folkweave/index.html", "tidings/index.html", "assets/folkweave-loom.webp", "assets/tidings-town-crier.png", "assets/folkweave-timeline.webp", "assets/tidings-reader.webp"):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "site"
                shutil.copytree(SITE, root)
                (root / relative).unlink()
                self.assertTrue(validate_site(root))

    def test_home_and_product_screenshots_reject_missing_metadata(self):
        for relative in ("index.html", "folkweave/index.html", "tidings/index.html"):
            original = (SITE / relative).read_text()
            apps = ["folkweave", "tidings"] if relative == "index.html" else [relative.split("/")[0]]
            self.assertEqual(project_screenshot_errors(Document(original), apps), [])
            for app in apps:
                for replacement in ('data-removed="'+app+'"', 'data-screenshot="missing"'):
                    with self.subTest(relative=relative, app=app, replacement=replacement):
                        mutated = original.replace('data-screenshot="'+app+'"', replacement)
                        self.assertTrue(project_screenshot_errors(Document(mutated), apps))

    def test_product_boundaries_reject_mutations(self):
        for app in ("folkweave", "tidings"):
            original = (SITE / app / "index.html").read_text()
            source = "https://github.com/airencracken/" + app
            mutations = [
                ("parental approval controls are not implemented" if app == "folkweave" else "A live indicator shows progress", "future work"),
            ]
            for before, after in mutations:
                with self.subTest(app=app, mutation=after):
                    self.assertIn(before, original)
                    self.assertTrue(initial_app_errors(Document(original.replace(before, after)), f"/{app}/"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
