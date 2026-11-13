"""Fictional screenshot media keeps provenance, originals and download budgets."""
import json
import re
from pathlib import Path
import unittest
from test_content import image_size

ROOT=Path(__file__).resolve().parents[2]
ASSETS=ROOT/'design/demo-assets'

class DemoAssetTests(unittest.TestCase):
    def test_originals_prompts_and_derivatives_are_preserved(self):
        manifest=json.loads((ASSETS/'provenance.json').read_text())
        self.assertEqual(manifest['tool'],'image_gen.imagegen')
        self.assertEqual(len(manifest['assets']),3)
        for entry in manifest['assets']:
            for key in ['file','original']:
                path=ASSETS/entry[key]
                self.assertTrue(path.resolve().is_relative_to(ASSETS.resolve()))
                self.assertTrue(path.is_file())
            self.assertGreater(len(entry['prompt']),80)
        for entry in manifest['derivatives']:
            self.assertTrue((ASSETS/entry['source']).is_file())
            self.assertTrue((ASSETS/entry['file']).is_file())

    def test_actual_screenshots_and_public_image_budgets(self):
        for name,dimensions in [('imvault-gallery',(1120,900)),('songstead-recent',(1280,1218)),('folkweave-timeline',(1280,1000)),('tidings-reader',(1280,1000)),('witmoot-board',(1280,1233))]:
            self.assertEqual(image_size(ROOT/'design/screenshots'/f'{name}.png'),dimensions)
            path=ROOT/'site/assets'/f'{name}.webp'
            self.assertEqual(image_size(path),dimensions)
            self.assertLess(path.stat().st_size,200000)
        self.assertLess((ROOT/'site/assets/imvault-gallery.png').stat().st_size,200000)

    def test_webp_is_smaller_than_its_png_twin(self):
        # Pages serve the WebP; a WebP larger than its PNG fallback wastes bytes.
        # Only same-size twins compare; some PNGs are larger social previews.
        pairs=[(w,w.with_suffix('.png')) for w in sorted((ROOT/'site/assets').glob('*.webp'))
               if w.with_suffix('.png').is_file() and image_size(w)==image_size(w.with_suffix('.png'))]
        self.assertTrue(any(w.name=='witmoot-board.webp' for w,_ in pairs))
        for webp,png in pairs:
            with self.subTest(image=webp.name):
                self.assertLess(webp.stat().st_size,png.stat().st_size)

    def test_mascot_brief_uses_the_site_palette(self):
        brief=(ROOT/'docs/mascot.md').read_text().split('## The comfy robot')[0]
        for phrase in ('An object with a face','One outline weight','The site palette'):
            self.assertIn(phrase,brief)
        css=(ROOT/'site/assets/site.css').read_text()
        tokens=dict(re.findall(r'--([\w-]+): light-dark\((#[0-9a-f]{6}),',css))
        colours=re.findall(r'^  - ([\w-]+) `(#[0-9a-f]{6})`$',brief,re.MULTILINE)
        self.assertGreaterEqual(len(colours),4)
        for name,value in colours:
            with self.subTest(colour=name):
                self.assertEqual(tokens.get(name),value,'brief colour must match the light site token')

if __name__=='__main__':unittest.main()
