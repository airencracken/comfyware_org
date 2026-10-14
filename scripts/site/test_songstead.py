"""Songstead's public promises, privacy boundaries, and screenshot contracts."""
from pathlib import Path
import shutil
import tempfile
import unittest

from test_content import Document, SITE, validate_site


class SongsteadTests(unittest.TestCase):
    def test_leads_with_the_gift_and_respects_peoples_time(self):
        text = (SITE / 'songstead/index.html').read_text()
        hero = text.split('<figure', 1)[0]
        self.assertIn('A recommendation is a gift,<br>never an assignment.', hero)
        self.assertIn('It can sit for six months without anything being wrong.', hero)
        for phrase in ('Extremely eventual consistency:', 'because your friends have lives.',
                       'No streaks, deadlines, unsolicited reminders, or playback tracking.',
                       'Opening a recommendation changes nothing.', 'does not host or stream music'):
            self.assertIn(phrase, text)

    def test_explains_private_likes_url_grouping_and_audiences(self):
        text = (SITE / 'songstead/index.html').read_text()
        for phrase in ('Matching URLs', 'who recommended it, when', 'Different providers stay separate.',
                       'No public like counts or listening receipts.', 'listening notes',
                       'Posting a recommendation marks it as listened for you.',
                       'There is no anonymous feed.', 'current members of its group',
                       'Owner status does not bypass these boundaries.', 'likes stay private.'):
            self.assertIn(phrase, text)
        self.assertEqual(text.count('<details>'), 2)

    def test_installation_and_operational_details_have_a_docs_home(self):
        text = (SITE / 'songstead/index.html').read_text()
        document = Document(text)
        links = {tag.get('href') for tag in document.tags['a']}
        for target in ('/songstead/docs/#install', '/songstead/docs/#backups', '/songstead/docs/#operate',
                       'https://github.com/airencracken/songstead/releases/latest'):
            self.assertIn(target, links)
        self.assertEqual([entry for entry in document.nav if entry[2] == 'page'],
                         [['/songstead/', 'Songstead', 'page']])
        self.assertNotIn('compact genre and tag pickers', text)
        self.assertNotIn('Open Your settings', text)

    def test_real_screenshot_is_linked_with_correct_dimensions(self):
        for path in ('index.html', 'songstead/index.html'):
            document = Document((SITE / path).read_text())
            screenshots = [tag for tag in document.tags['img'] if tag.get('src') == '/assets/songstead-recent.webp']
            self.assertEqual(len(screenshots), 1)
            self.assertEqual((screenshots[0]['width'], screenshots[0]['height']), ('1280', '1289'))
            self.assertIn('recommendations', screenshots[0]['alt'])
        self.assertIn('fictional music, local sample artwork and demo accounts', (SITE / 'songstead/index.html').read_text())

    def test_missing_route_and_artwork_fail_validation(self):
        for path in ('songstead/index.html', 'songstead/docs/index.html', 'assets/songstead-jukebox.png', 'assets/songstead-recent.webp'):
            with self.subTest(path=path), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'site'
                shutil.copytree(SITE, root)
                (root / path).unlink()
                self.assertTrue(validate_site(root))

    def test_malformed_metadata_dimensions_and_injected_content_are_rejected(self):
        for old, new in [('https://comfyware.org/songstead/', 'https://example.org/songstead/'),
                         ('<body', '<body onload="alert(1)"'), ('height="1289"', 'height="480"')]:
            with self.subTest(old=old), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / 'site'
                shutil.copytree(SITE, root)
                page = root / 'songstead/index.html'
                original = page.read_text()
                mutated = original.replace(old, new, 1)
                self.assertNotEqual(original, mutated)
                page.write_text(mutated)
                self.assertTrue(validate_site(root))


if __name__ == '__main__':
    unittest.main(verbosity=2)
