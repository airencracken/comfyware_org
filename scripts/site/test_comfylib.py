"""Library discovery, module installation, release schema and damaged content."""
from pathlib import Path
import shutil
import tempfile
import unittest

from test_content import Document, SITE, library_errors, release_errors, release_versions, validate_site


class ComfylibTests(unittest.TestCase):
    def test_library_page_and_homepage_contracts(self):
        versions = release_versions()
        for route, relative in (("/", "index.html"), ("/comfylib/", "comfylib/index.html")):
            doc = Document((SITE / relative).read_text())
            self.assertEqual(library_errors(doc, route, versions), [])
            self.assertEqual(release_errors(doc, list(versions) if route == "/" else ["comfylib"], versions), [])

    def test_missing_discovery_and_damaged_module_commands_are_rejected(self):
        versions = release_versions()
        home = (SITE / "index.html").read_text().replace('href="/comfylib/"', 'href="/"')
        self.assertTrue(library_errors(Document(home), "/", versions))
        original = (SITE / "comfylib/index.html").read_text()
        command = f"go get github.com/airencracken/comfylib@v{versions['comfylib']}"
        for replacement in ("go get github.com/airencracken/comfylib@latest", "go get example.org/other@v0.1.7", "go get github.com/airencracken/comfylib@../private", "&lt;script&gt;"):
            with self.subTest(replacement=replacement):
                self.assertTrue(library_errors(Document(original.replace(command, replacement)), "/comfylib/", versions))
        duplicate = original.replace('</main>', f'<code data-module="comfylib">{command}</code></main>')
        self.assertTrue(library_errors(Document(duplicate), "/comfylib/", versions))

    def test_shipping_validator_rejects_library_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "site"
            shutil.copytree(SITE, root)
            page = root / "comfylib/index.html"
            original = page.read_text()
            for before, after in (
                ('data-module="comfylib"', 'data-module="other"'),
                ('href="https://pkg.go.dev/github.com/airencracken/comfylib"', 'href="https://example.org/"'),
                ('data-release="comfylib"', 'data-release="imvault"'),
                ('href="/imvault/"', 'href="javascript:alert(1)"'),
            ):
                with self.subTest(mutation=after):
                    self.assertIn(before, original)
                    page.write_text(original.replace(before, after))
                    self.assertTrue(validate_site(root))
            page.write_text(original)
            self.assertEqual(validate_site(root), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
