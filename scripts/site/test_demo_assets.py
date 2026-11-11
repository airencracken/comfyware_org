"""Fictional screenshot media keeps provenance, originals and download budgets."""
import json
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

if __name__=='__main__':unittest.main()
