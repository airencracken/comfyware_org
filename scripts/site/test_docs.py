"""Docs discovery, editorial budgets, route/schema contracts and regressions."""
from pathlib import Path
import re
import shutil
import tempfile
import unittest

from test_content import Document, SITE, container_errors, editorial_errors, validate_site

APPS = ('imvault', 'witmoot', 'songstead')


class DocumentationTests(unittest.TestCase):
    def test_each_app_has_a_discoverable_docs_page(self):
        home = Document((SITE / 'index.html').read_text())
        home_links = {attrs.get('href') for attrs in home.tags['a']}
        for app in APPS:
            with self.subTest(app=app):
                self.assertIn(f'/{app}/docs/', home_links)
                for kind in ('', 'docs/'):
                    route = f'/{app}/{kind}'
                    doc = Document((SITE / app / kind / 'index.html').read_text())
                    self.assertEqual(editorial_errors(doc, route), [])
                    self.assertEqual([link[0] for link in doc.nav if link[2] == 'page'], [f'/{app}/'])
                docs = Document((SITE / app / 'docs/index.html').read_text())
                self.assertIn(f'/{app}/', {attrs.get('href') for attrs in docs.tags['a']})

    def test_published_images_are_discoverable_from_home_products_and_docs(self):
        for app in APPS:
            for relative, route in (('index.html', '/'), (f'{app}/index.html', f'/{app}/'),
                                    (f'{app}/docs/index.html', f'/{app}/docs/')):
                doc = Document((SITE / relative).read_text())
                self.assertEqual(container_errors(doc, route), [])
                link = [attrs for attrs, text in doc.links if attrs.get('data-container') == app]
                self.assertEqual(len(link), 1)
                self.assertEqual(link[0]['href'], f'https://github.com/airencracken/{app}/blob/master/docs/containers.md')
            docs = (SITE / app / 'docs/index.html').read_text()
            self.assertIn('amd64 or arm64', docs)
            self.assertIn('version pins', docs)
            self.assertIn(f'https://github.com/airencracken/{app}/pkgs/container/{app}', docs)

    def test_container_link_schema_rejects_missing_duplicate_and_wrong_app_guides(self):
        for app in APPS:
            for relative, route in (('index.html', '/'), (f'{app}/index.html', f'/{app}/'),
                                    (f'{app}/docs/index.html', f'/{app}/docs/')):
                text = (SITE / relative).read_text()
                guide = f'https://github.com/airencracken/{app}/blob/master/docs/containers.md'
                for before, after in ((f'data-container="{app}"', 'data-removed="gone"'),
                                      (guide, 'https://github.com/airencracken/other/blob/master/docs/containers.md'),
                                      (guide, 'javascript:alert(1)'), (guide, '//example.org/install'),
                                      (guide, 'https://example.org/%2e%2e/install')):
                    with self.subTest(app=app, route=route, mutation=after):
                        changed = text.replace(before, after, 1)
                        self.assertNotEqual(changed, text)
                        self.assertTrue(container_errors(Document(changed), route))
                duplicate = f'<a data-container="{app}" href="{guide}">Docker Compose</a>'
                self.assertTrue(container_errors(Document(text.replace('</main>', duplicate+'</main>')), route))
            text = (SITE / app / 'docs/index.html').read_text()
            wrong_package = text.replace(f'/{app}/pkgs/container/{app}', '/other/pkgs/container/other')
            self.assertTrue(container_errors(Document(wrong_package), f'/{app}/docs/'))

    def test_container_regressions_fail_the_shipping_validator(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'site'
            shutil.copytree(SITE, root)
            page = root / 'songstead/docs/index.html'
            page.write_text(page.read_text().replace('data-container="songstead"', 'data-removed="songstead"'))
            self.assertTrue(any('Expected one Docker' in error for error in validate_site(root)))

    def test_docs_schema_rejects_missing_topics_and_maintained_guides(self):
        for app in APPS:
            text = (SITE / app / 'docs/index.html').read_text()
            for target in ('install', 'operate', 'backups', 'upgrades', 'help'):
                for before, after in ((f'id="{target}"', f'id="missing-{target}"'),
                                      (f'href="#{target}"', 'href="#missing"')):
                    with self.subTest(app=app, target=before):
                        changed = text.replace(before, after)
                        self.assertNotEqual(text, changed)
                        self.assertTrue(editorial_errors(Document(changed), f'/{app}/docs/'))
            for path in ('releases.md', 'deployment.md', 'automatic-backups.md'):
                before = f'/{app}/blob/master/docs/{path}'
                changed = text.replace(before, '/other-app/blob/master/docs/'+path)
                self.assertNotEqual(text, changed)
                self.assertTrue(editorial_errors(Document(changed), f'/{app}/docs/'))

    def test_product_copy_budget_at_the_boundary(self):
        links = '<a href="/songstead/docs/#install">Install</a><a href="/songstead/docs/#backups">Backups</a>'
        for words in (0, 647, 648, 649, 650, 651, 900):
            doc = Document('<main>'+links+'<p>'+'word '*words+'</p></main>')
            with self.subTest(words=words):
                self.assertEqual(any('word budget' in err for err in editorial_errors(doc, '/songstead/')), words+2 > 650)

    def test_release_specific_prose_is_rejected_but_release_links_are_allowed(self):
        for app in APPS:
            original = (SITE / app / 'index.html').read_text()
            for version in ('0.1.0', '0.10.0', '99.100.1000'):
                changed = original.replace('</main>', f'<p>In {app} {version}, open settings.</p></main>')
                self.assertTrue(any('release notes' in e for e in editorial_errors(Document(changed), f'/{app}/')))
            self.assertEqual(editorial_errors(Document(original), f'/{app}/'), [])

    def test_editorial_regressions_fail_the_shipping_validator(self):
        for relative, before, after, expected in (
            ('songstead/index.html', '</main>', '<p>In Songstead 0.10.0, use this switch.</p></main>', 'Version-specific'),
            ('imvault/index.html', '</main>', '<p>'+'extra '*651+'</p></main>', 'word budget'),
            ('witmoot/docs/index.html', 'id="backups"', 'id="other"', 'expose the backups'),
            ('songstead/index.html', '/songstead/docs/#install', '/songstead/', 'link to install'),
        ):
            with self.subTest(relative=relative), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'site'
                shutil.copytree(SITE, root)
                page = root / relative
                self.assertIn(before, page.read_text())
                page.write_text(page.read_text().replace(before, after, 1))
                self.assertTrue(any(expected in e for e in validate_site(root)))

    def test_homepage_and_error_recovery_include_all_apps(self):
        home = (SITE / 'index.html').read_text()
        doc = Document(home)
        preview = next(tag['content'] for tag in doc.tags['meta'] if tag.get('property') == 'og:description')
        self.assertIn('music', preview)
        faq = re.search(r'Do I need to run every app\?</summary><p>(.*?)</p>', home)[1]
        moderation = re.search(r'Your community’s own judgment</h3><p>(.*?)</p>', home)[1]
        missing = Document((SITE / '404.html').read_text())
        for app in APPS:
            self.assertIn(app.capitalize(), faq)
            self.assertIn(app.capitalize(), moderation)
            self.assertIn(f'/{app}/', {attrs.get('href') for attrs, text in missing.links if text == app.capitalize()})

    def test_imvault_library_guides_and_evergreen_features_are_discoverable(self):
        docs = Document((SITE / 'imvault/docs/index.html').read_text())
        self.assertIn('https://github.com/airencracken/imvault/blob/master/docs/library.md',
                      {attrs.get('href') for attrs in docs.tags['a']})
        product = (SITE / 'imvault/index.html').read_text()
        for feature in ('date taken', 'batches', 'Trash'):
            self.assertIn(feature, product)
        self.assertEqual(editorial_errors(Document(product), '/imvault/'), [])

    def test_maintainer_and_contact_are_public(self):
        home = (SITE / 'index.html').read_text()
        self.assertIn('Made by <a href="https://github.com/airencracken">Marcus</a>', home)
        self.assertIn('https://github.com/airencracken/comfyware_org/issues', home)


if __name__ == '__main__':
    unittest.main(verbosity=2)
