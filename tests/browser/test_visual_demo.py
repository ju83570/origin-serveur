"""Recette de l'archive visuelle sur HTTP loopback, sans moteur ni fournisseur."""
from pathlib import Path
import json
import subprocess
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]


class PortableDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        class Handler(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),partial(Handler,directory=str(ROOT/'demo-visual')))
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join(timeout=2)

    def test_portable_demo_mirror_free_journey_premium_and_export_without_external_network(self):
        context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        self.addCleanup(context.close)
        page=context.new_page();external=[];errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        def guard(route):
            if route.request.url.startswith(('http:','https:')) and urlparse(route.request.url).netloc!=urlparse(self.base).netloc:external.append(route.request.url);route.abort()
            else:route.continue_()
        page.route('**/*',guard)
        page.goto(self.base+'/index.html')
        self.assertIn('Aucun paiement',page.locator('body').inner_text())
        page.locator('.nav-item[data-go="miroir"]').click()
        page.locator('#nameA').fill('Camille');page.locator('#nameB').fill('Alex')
        page.locator('[data-step-jump="2"]').click();page.locator('#messageA').fill('Un moment pour écouter.')
        page.locator('#revealBtn').click()
        output=Path('/tmp/origin-vivant-screenshots');output.mkdir(exist_ok=True)
        page.screenshot(path=str(output/'demo-autonome-miroir-mobile.png'),full_page=True)
        page.locator('.nav-item[data-go="parcours"]').click()
        page.locator('#dailyNote').fill('Un premier pas.');page.locator('#saveCheckin').click()
        page.locator('.nav-item[data-go="premium"]').click()
        self.assertEqual(page.get_by_role('link',name='Voir le PDF Solo').count(),1)
        page.locator('#premiumSource').select_option('mirror');page.locator('#premiumConsent').check()
        with page.expect_download() as download:page.locator('#premiumExport').click()
        data=json.loads(Path(download.value.path()).read_text())
        self.assertEqual(data['clients'][0]['prenom'],'Camille')
        self.assertLessEqual(page.evaluate('document.documentElement.scrollWidth'),391)
        page.screenshot(path=str(output/'demo-autonome-premium-mobile.png'),full_page=True)
        self.assertEqual(external,[]);self.assertEqual(errors,[])

    def test_portable_pdfs_are_real_and_explicitly_demonstrations(self):
        for offer in ['solo','couple']:
            path=ROOT/f'demo-visual/{offer}-demonstration.pdf'
            self.assertTrue(path.read_bytes().startswith(b'%PDF-'))
            text=subprocess.check_output(['pdftotext',str(path),'-']).decode()
            self.assertIn('Camille',text)
            self.assertIn('DÉMONSTRATION',text)
            if offer=='couple':self.assertIn('Alex',text)


if __name__=='__main__':unittest.main()
