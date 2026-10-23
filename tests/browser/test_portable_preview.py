"""Un seul fichier chargé : aucune autre ressource ou requête applicative."""
import json
import os
from pathlib import Path
import subprocess
import unittest

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


class PortablePreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = subprocess.Popen(
            ['node', str(ROOT / 'web-preview/preview-server.cjs')],
            env={**os.environ, 'ORIGIN_PREVIEW_PORT': '0', 'ORIGIN_PREVIEW_HOST': '127.0.0.1'},
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = json.loads(cls.server.stdout.readline())
        cls.url = 'http://127.0.0.1:' + str(ready['port']) + '/ORIGIN_DEMO.html'
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(
            executable_path='/usr/bin/chromium', headless=True,
            args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()
        cls.server.terminate()
        cls.server.communicate(timeout=10)

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 390, 'height': 844})
        self.addCleanup(self.context.close)
        self.context.add_init_script("localStorage.setItem('origin_vivant_local_v1','FICTIF À PRÉSERVER');")
        self.page = self.context.new_page()
        self.errors = []
        self.network = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))

        def guard(route):
            if route.request.url.split('#')[0] != self.url:
                self.network.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        self.page.route('**/*', guard)
        self.page.goto(self.url)

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.network, [])
        self.assertEqual(self.page.evaluate("localStorage.getItem('origin_vivant_local_v1')"), 'FICTIF À PRÉSERVER')

    def go(self, view):
        self.page.locator('.nav-item[data-go="' + view + '"]').click()

    def tree(self):
        self.go('arbre')
        self.page.get_by_role('link', name='Ouvrir mon Arbre Vivant').click()
        tree = self.page.frame_locator('#portableTreeFrame')
        tree.locator('.tree-card').first.wait_for()
        return tree

    def test_all_four_experiences_without_network_or_external_assets(self):
        for view in ['miroir', 'arbre', 'carnet', 'constellation']:
            self.go(view)
            self.assertTrue(self.page.locator('#view-' + view).is_visible())
        self.assertEqual(self.page.locator('script[src],link[href]:not([href^="data:"]),img[src]:not([src^="data:"])').count(), 0)
        self.assertEqual(self.tree().locator('.tree-card').count(), 5)

    def test_carnet_persistence_and_reset_from_tree_preserve_other_keys(self):
        self.go('carnet')
        self.page.locator('#writePage').click()
        self.page.locator('#pageText').fill('Un souvenir inventé pour la démo autonome.')
        self.page.locator('#savePage').click()
        self.page.reload()
        self.assertIn('démo autonome', self.page.locator('#pageList').inner_text())
        tree = self.tree()
        self.page.once('dialog', lambda dialog: dialog.accept())
        tree.locator('#previewReset').click()
        self.page.wait_for_url('**/ORIGIN_DEMO.html#accueil')
        self.go('carnet')
        self.assertEqual(self.page.locator('.page-record').count(), 1)

    def test_tree_constellation_mirror_round_trip(self):
        tree = self.tree()
        tree.locator('.tree-card[data-id="camille"]').click()
        tree.locator('#profileConstellation').click()
        self.page.locator('#view-constellation').wait_for(state='visible')
        self.assertFalse(self.page.locator('#portableTree').is_visible())
        self.page.locator('#constellationPersonB').select_option('francoise')
        self.assertIn('parent', self.page.locator('#constellationLink').inner_text())
        self.page.locator('#constellationBack').click()
        self.assertIn('Camille', self.page.frame_locator('#portableTreeFrame').locator('#profileName').inner_text())
        self.page.locator('#portableTreeClose').click()
        self.page.locator('#constellationMirror').click()
        self.assertEqual(self.page.locator('#birthB').input_value(), '1958-03-14')

    def test_mobile_navigation_has_no_overflow(self):
        for width in [320, 390, 768, 1440]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            for view in ['miroir', 'arbre', 'carnet', 'constellation']:
                self.go(view)
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width + 1)

    def test_html_reader_distant_base_cannot_break_history_navigation(self):
        source = (ROOT / 'web-preview/ORIGIN_DEMO.html').read_text()
        source = source.replace('<head>', '<head><base href="https://raw.githubusercontent.com/ju83570/origin-serveur/origin-preview-demo/ORIGIN_DEMO.html">', 1)
        self.page.route(self.url, lambda route: route.fulfill(status=200, content_type='text/html', body=source))
        self.page.goto(self.url)
        self.go('carnet')
        self.assertTrue(self.page.locator('#view-carnet').is_visible())
        self.assertEqual(self.page.url, self.url + '#carnet')


if __name__ == '__main__':
    unittest.main(verbosity=2)
