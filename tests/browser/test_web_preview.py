"""Aperçu public statique : uniquement des fixtures, aucun backend accessible."""
import hashlib
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
import threading
import unittest
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
DIRECTORY=ROOT/'web-preview'


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


class WebPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.output=TemporaryDirectory(prefix='origin-web-preview-test-')
        shutil.copytree(DIRECTORY,Path(cls.output.name)/'origin-serveur')
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=cls.output.name))
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)+'/origin-serveur'
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop();cls.server.shutdown();cls.server.server_close();cls.thread.join();cls.output.cleanup()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        self.addCleanup(self.context.close)
        # Sentinelles fictives : prouver l'isolation des stockages de l'application.
        self.context.add_init_script("if(!localStorage.getItem('origin_vivant_local_v1'))localStorage.setItem('origin_vivant_local_v1','COPIE FICTIVE À PRÉSERVER');")
        self.page=self.context.new_page();self.errors=[];self.external=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        def guard(route):
            if urlparse(route.request.url).netloc!=urlparse(self.base).netloc:
                self.external.append(route.request.url);route.abort()
            else:route.continue_()
        self.page.route('**/*',guard);self.page.goto(self.base+'/')

    def tearDown(self):
        self.assertEqual(self.errors,[]);self.assertEqual(self.external,[])
        self.assertEqual(self.page.evaluate("localStorage.getItem('origin_vivant_local_v1')"),'COPIE FICTIVE À PRÉSERVER')

    def go(self,view):self.page.locator('.nav-item[data-go="'+view+'"]').click()

    def test_actual_sources_and_all_four_experiences_are_available(self):
        self.assertIn('Personnages fictifs',self.page.locator('.preview-banner').inner_text())
        for view in ['miroir','arbre','carnet','constellation']:
            self.go(view);self.assertTrue(self.page.locator('#view-'+view).is_visible())
        self.assertEqual(self.page.locator('#constellationPersonA').input_value(),'camille')
        self.assertEqual(self.page.locator('#constellationPersonB').input_value(),'alex')
        manifest=json.loads((DIRECTORY/'manifest.json').read_text())
        for name,digest in manifest['source_sha256'].items():self.assertEqual(hashlib.sha256((ROOT/'hostinger/vivant'/name).read_bytes()).hexdigest(),digest)

    def test_carnet_writing_reload_and_isolated_storage(self):
        self.go('carnet');self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Une réflexion entièrement fictive pour tester cet aperçu.')
        self.page.locator('#savePage').click();self.page.reload()
        self.assertIn('entièrement fictive',self.page.locator('#pageList').inner_text())
        self.assertEqual(len(self.page.evaluate("JSON.parse(localStorage.getItem('origin_web_preview_carnet_v1')).pages")),2)

    def test_tree_constellation_mirror_flow_without_retyping_dates(self):
        self.go('arbre');self.page.get_by_role('link',name='Ouvrir mon Arbre Vivant').click()
        self.page.locator('.tree-card').first.wait_for(state='visible')
        self.assertEqual(self.page.locator('.tree-card').count(),5)
        self.page.locator('.tree-card[data-id="camille"]').click();self.page.locator('#profileConstellation').click()
        self.page.locator('#view-constellation').wait_for(state='visible')
        self.assertEqual(self.page.locator('#constellationPersonA').input_value(),'camille')
        self.page.locator('#constellationPersonB').select_option('francoise')
        self.assertIn('parent',self.page.locator('#constellationLink').inner_text())
        self.page.locator('#constellationMirror').click()
        self.assertEqual(self.page.locator('#birthB').input_value(),'1958-03-14')
        self.page.locator('[data-step-jump="3"]').click()
        self.assertIn('Cette personne n’a pas encore pris la parole',self.page.locator('#mirrorResult').inner_text())

    def test_payments_accounts_and_external_api_are_not_exposed(self):
        self.assertEqual(self.page.locator('script[src="origin-commercial.js"]').count(),0)
        self.assertEqual(self.page.locator('[data-account]').count(),0)
        policy=self.page.locator('meta[http-equiv="Content-Security-Policy"]').get_attribute('content')
        self.assertIn("connect-src 'none'",policy)
        for path in ['/api/?op=checkout','/api/bootstrap.php','/app.py','/.env','/origin-commercial.js']:
            self.assertEqual(self.context.request.get(self.base+path).status,404)
        self.assertEqual(self.context.request.post(self.base+'/api/?op=checkout',data='{}').status,501)
        self.assertEqual(self.page.locator('a[href^="https://origin-famille.fr"]').count(),0)

    def test_reset_from_the_tree_only_resets_the_demo_namespace(self):
        self.go('carnet');self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Page fictive temporaire.');self.page.locator('#savePage').click()
        self.page.goto(self.base+'/arbre-vivant.html')
        self.page.once('dialog',lambda dialog:dialog.accept());self.page.locator('#previewReset').click()
        self.page.wait_for_url('**/#accueil')
        self.go('carnet');self.assertEqual(self.page.locator('.page-record').count(),1)

    def test_mobile_and_desktop_navigation_have_no_page_overflow(self):
        for width in [320,390,768,1440]:
            self.page.set_viewport_size({'width':width,'height':900})
            for view in ['miroir','arbre','carnet','constellation']:
                self.go(view);self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1,(width,view))


if __name__=='__main__':unittest.main(verbosity=2)
