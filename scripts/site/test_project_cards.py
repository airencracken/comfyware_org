"""Keep the five home cards equally useful and visually consistent."""
from html.parser import HTMLParser
from pathlib import Path
import re
import unittest

# Every card's demo link uses the same docs anchor; facts.json keeps the
# app-specific README headings in one place.
DEMOS = ('imvault', 'witmoot', 'songstead', 'folkweave', 'tidings')
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
        expected = [f'/{app}/', f'/{app}/docs/#demo',
                    f'/{app}/docs/', f'https://github.com/airencracken/{app}/blob/master/docs/containers.md']
        if card['links'][:4] != expected:
            errors.append(app + ': expected Meet, local demo, docs and Docker actions in that order')
        if card['preview'] != 'project-preview':
            errors.append(app + ': preview must use the shared frame styling')
    captions = re.findall(r'<figcaption>(.*?)</figcaption>', text)
    pattern = r'[A-Z][^.·<]*, with (?:fictional|sample) [^.·<]+ · <a href="/assets/[\w-]+\.webp">Full screenshot</a>'
    if len(captions) != 5 or not all(re.fullmatch(pattern, caption) for caption in captions):
        errors.append('Card captions must read "What it shows, with fictional content · Full screenshot"')
    if text.count('>Try the local demo</a>') != 5:
        errors.append('Expected five consistently labeled local demo links')
    taglines = re.findall(r'<h3 id="(\w+)-title">.*?</div>\s*<p class="project-tagline">[^<]+</p>', text, re.DOTALL)
    if taglines != list(DEMOS):
        errors.append('Every card needs a tagline under its title')
    return errors


def arise_errors(text):
    """Arise is experimental tooling, so it gets a note, not a card or hero spot."""
    errors = []
    if re.search(r'<h[1-3][^>]*>\s*<a href="https://github.com/airencracken/arise"', text):
        errors.append('Arise must not have its own heading on the homepage')
    if not re.search(r'<p class="workshop-note">[^\n]*data-release="arise"', text):
        errors.append('Arise release belongs in the workshop note')
    return errors


def template_errors(text, app):
    """Hold every product page to the same sections, in the same order."""
    name = app.capitalize()
    checks = [
        ('eyebrow', rf'<p class="eyebrow">{name} · [^<]+</p><h1 id="welcome">[^<]+<br>[^<]+</h1>'),
        ('get started button', rf'<a class="button" href="/{app}/docs/#install">Get started with {name} <span aria-hidden="true">&nbsp;→</span></a>'),
        ('screenshot caption', rf'<figcaption>[^<]+ <a href="/assets/[\w-]+\.webp">View the full screenshot</a>\.</figcaption>'),
        ('features', r'<div class="section-heading"><h2 id="features-heading">[^<]+</h2></div><div class="features">'),
        ('backups', r'<h2 id="backups-heading">A copy worth keeping\.</h2>'),
        ('getting started', r'<section id="getting-started" class="section getting-started" aria-labelledby="start-heading"><div><p class="eyebrow">Make it yours</p>'),
        ('other project', r'<aside class="other-project"><p>[^<]+</p><a class="text-link" href="/\w+/">Meet \w+ <span aria-hidden="true">→</span></a></aside>'),
    ]
    errors = []
    position = 0
    for label, pattern in checks:
        match = re.compile(pattern).search(text, position)
        if not match:
            errors.append(f'{app}: missing or out-of-order {label}')
        else:
            position = match.end()
    steps = re.search(r'<ol class="steps">(.*?)</ol>', text, re.DOTALL)
    if not steps or steps[1].count('<li>') != 3:
        errors.append(f'{app}: getting started needs three steps')
    return errors


class ProjectCardTests(unittest.TestCase):
    def test_all_cards_have_the_same_actions_and_frame(self):
        self.assertEqual(card_errors((SITE / 'index.html').read_text()), [])

    def test_missing_wrong_duplicate_or_mislabeled_demo_is_detected(self):
        original = (SITE / 'index.html').read_text()
        for app in DEMOS:
            link = f'<a href="/{app}/docs/#demo">Try the local demo</a>'
            for replacement in ('', link + link, link.replace('#demo', '#try-it'), link.replace(f'/{app}/', '/other/'),
                                link.replace('Try the local demo', 'Demo')):
                with self.subTest(app=app, replacement=replacement):
                    self.assertTrue(card_errors(original.replace(link, replacement, 1)))

    def test_product_pages_share_one_template(self):
        for app in DEMOS:
            with self.subTest(app=app):
                self.assertEqual(template_errors((SITE / app / 'index.html').read_text(), app), [])

    def test_template_mutations_are_detected(self):
        text = (SITE / 'tidings/index.html').read_text()
        for before, after in (('<p class="eyebrow">Tidings · ', '<p class="eyebrow">'),
                              ('A copy worth keeping.', 'Backups and recovery.'),
                              ('<p class="eyebrow">Make it yours</p>', ''),
                              ('<li><strong>Pull up a chair.</strong>', '<li hidden><strong>Pull up a chair.</strong>'),
                              ('View the full screenshot</a>.</figcaption>', '</a></figcaption>'),
                              ('<aside class="other-project">', '<aside>')):
            with self.subTest(before=before):
                self.assertIn(before, text)
                self.assertTrue(template_errors(text.replace(before, after, 1), 'tidings'))
        home = (SITE / 'index.html').read_text()
        self.assertTrue(card_errors(home.replace('<p class="project-tagline">The news you chose', '<p>The news you chose', 1)))

    def test_arise_stays_a_quiet_workshop_note(self):
        home = (SITE / 'index.html').read_text()
        self.assertEqual(arise_errors(home), [])
        promoted = home.replace('<p class="workshop-note">Also on the workbench: <a href="https://github.com/airencracken/arise">Arise</a>',
                                '<div><h3><a href="https://github.com/airencracken/arise">Arise</a></h3><p>', 1)
        self.assertNotEqual(promoted, home)
        self.assertTrue(arise_errors(promoted))
        self.assertTrue(arise_errors(home.replace('class="workshop-note"', 'class="hero-note"', 1)))

    def test_card_caption_mutations_are_detected(self):
        home = (SITE / 'index.html').read_text()
        for before, after in (('The timeline, with fictional posts and photos ·', 'The timeline, with fictional posts and photos. ·'),
                              ('The reading table, with fictional stories ·', 'A look inside · the reading table ·'),
                              ('>Full screenshot</a></figcaption>', '>View it</a></figcaption>')):
            with self.subTest(before=before):
                self.assertIn(before, home)
                self.assertTrue(card_errors(home.replace(before, after, 1)))

    def test_theme_tokens_are_written_once(self):
        css = (SITE / 'assets/site.css').read_text()
        names = re.findall(r'(--[\w-]+)\s*:', css)
        self.assertTrue(names)
        self.assertEqual(len(names), len(set(names)), 'a theme token is defined twice')
        for name, value in re.findall(r'(--[\w-]+)\s*:\s*([^;]+);', css):
            with self.subTest(token=name):
                self.assertRegex(value, r'^light-dark\(#[0-9a-f]{6}, #[0-9a-f]{6}\)$')
        self.assertEqual(len(re.findall(r'\{ color-scheme: dark; \}', css)), 2, 'dark mode needs the device and picker switches')

    def test_per_app_frame_mutation_is_detected(self):
        original = (SITE / 'index.html').read_text()
        self.assertTrue(card_errors(original.replace('class="project-preview"', 'class="project-preview witmoot"', 1)))
        css = (SITE / 'assets/site.css').read_text()
        self.assertIsNone(re.search(r'\.(?:project-preview|screenshot)\.[\w-]+\s*\{', css))


if __name__ == '__main__':
    unittest.main(verbosity=2)
