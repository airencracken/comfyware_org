"""Keep the five home cards equally useful and visually consistent."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

DEMOS = {'imvault': 'come-on-in', 'witmoot': 'come-on-in',
         'songstead': 'build-and-try-it', 'folkweave': 'try-it', 'tidings': 'try-the-demo'}
SITE = Path(__file__).resolve().parents[2] / 'site'


class Cards(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.cards, self.current = [], None
        self.in_links = False
        self.feed(text)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == 'article' and 'project' in attrs.get('class', '').split():
            self.current = {'app': attrs.get('aria-labelledby', '').removesuffix('-title'), 'links': [], 'preview': None}
            self.cards.append(self.current)
        if self.current is not None:
            if tag == 'div' and attrs.get('class') == 'project-links':
                self.in_links = True
            if tag == 'a' and self.in_links:
                self.current['links'].append(attrs.get('href'))
            if tag == 'figure':
                self.current['preview'] = attrs.get('class')

    def handle_endtag(self, tag):
        if tag == 'div':
            self.in_links = False
        if tag == 'article':
            self.current = None


def card_errors(text):
    cards = Cards(text).cards
    errors = []
    if [card['app'] for card in cards] != list(DEMOS):
        errors.append('Expected the same five application cards in order')
    for card in cards:
        app = card['app']
        if app not in DEMOS:
            continue
        expected = [f'/{app}/', f'https://github.com/airencracken/{app}#{DEMOS[app]}',
                    f'/{app}/docs/', f'https://github.com/airencracken/{app}/blob/master/docs/containers.md']
        if card['links'][:4] != expected:
            errors.append(app + ': expected Meet, local demo, docs and Docker actions in that order')
        if card['preview'] != 'project-preview':
            errors.append(app + ': preview must use the shared frame styling')
    if text.count('>Try the local demo</a>') != 5:
        errors.append('Expected five consistently labeled local demo links')
    return errors


class ProjectCardTests(unittest.TestCase):
    def test_all_cards_have_the_same_actions_and_frame(self):
        self.assertEqual(card_errors((SITE / 'index.html').read_text()), [])

    def test_missing_wrong_duplicate_or_mislabeled_demo_is_detected(self):
        original = (SITE / 'index.html').read_text()
        for app, anchor in DEMOS.items():
            href = f'https://github.com/airencracken/{app}#{anchor}'
            link = f'<a href="{href}">Try the local demo</a>'
            for replacement in ('', link + link, link.replace(app + '#', 'other#'), link.replace('Try the local demo', 'Demo')):
                with self.subTest(app=app, replacement=replacement):
                    self.assertTrue(card_errors(original.replace(link, replacement, 1)))

    def test_per_app_frame_mutation_is_detected(self):
        original = (SITE / 'index.html').read_text()
        self.assertTrue(card_errors(original.replace('class="project-preview"', 'class="project-preview witmoot"', 1)))
        css = (SITE / 'assets/site.css').read_text()
        self.assertIsNone(re.search(r'\.(?:project-preview|screenshot)\.[\w-]+\s*\{', css))


if __name__ == '__main__':
    unittest.main(verbosity=2)
