"""Tests navigateur réels, sur la façade LOCALE démarrée au port 5080."""
import json
import os
from pathlib import Path
import secrets
import sys
import unittest
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.vivant.local_stack import docker,sql,PHP

BASE = os.environ.get('ORIGIN_BROWSER_URL', 'http://127.0.0.1:5080')
OUTPUT = Path('/tmp/origin-vivant-screenshots')


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if urlparse(BASE).hostname not in ('127.0.0.1', 'localhost'):
            raise ValueError('Tests navigateur réservés au serveur local')
        cls.playwright = sync_playwright().start()
        cls.browser = cls.playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        OUTPUT.mkdir(exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.playwright.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width':390,'height':844}, reduced_motion='reduce')
        self.addCleanup(self.context.close)
        self.page = self.context.new_page()
        self.errors, self.external = [], []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        def guard(route):
            if urlparse(route.request.url).netloc != urlparse(BASE).netloc:
                self.external.append(route.request.url)
                route.abort()
            else:
                route.continue_()
        self.page.route('**/*', guard)
        self.page.goto(BASE+'/vivant/')

    def tearDown(self):
        self.assertEqual(self.errors, [])
        self.assertEqual(self.external, [])

    def go(self, view):
        self.page.locator(f'.nav-item[data-go="{view}"]').click()

    def test_mobile_navigation_and_no_page_overflow(self):
        for width in (320,390,768,1440):
            self.page.set_viewport_size({'width':width,'height':900})
            for view in ('accueil','miroir','arbre','parcours','carnet','premium'):
                self.go(view)
                self.assertTrue(self.page.locator('#view-'+view).is_visible())
                self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width+1, (width,view))
            if width==390:
                self.page.screenshot(path=str(OUTPUT/'mobile-premium.png'),full_page=True)

    def test_real_mirror_journey_export_and_injection_escape(self):
        self.go('miroir')
        self.page.locator('#nameA').fill('Lina')
        self.page.locator('#nameB').fill('Noé')
        self.page.locator('[data-step-jump="2"]').click()
        self.page.locator('#messageA').fill('<img src=x onerror="window.injected=true">')
        self.page.locator('#revealBtn').click()
        self.assertIn('Cette personne n’a pas encore pris la parole', self.page.locator('#mirrorResult').inner_text())
        self.assertEqual(self.page.locator('#mirrorResult img').count(),0)
        self.assertFalse(self.page.evaluate('window.injected === true'))
        self.page.locator('[data-step-jump="4"]').click()
        self.page.locator('#commitText').fill('Écouter sans interrompre.')
        self.page.locator('#saveMirror').click()
        self.go('parcours')
        self.page.locator('#dailyNote').fill('Un moment pour écouter.')
        self.page.locator('#saveCheckin').click()
        self.go('carnet')
        self.assertEqual(self.page.locator('#statMirrors').inner_text(),'1')
        self.assertEqual(self.page.locator('#statCheckins').inner_text(),'1')
        with self.page.expect_download() as download:
            self.page.locator('#exportJson').click()
        export = json.loads(Path(download.value.path()).read_text())
        self.assertEqual(export['format'],'origin-vivant-cloud-2')
        self.assertEqual(export['carnet']['mirrors'][0]['nameA'],'Lina')

    def test_demo_is_explicit_and_cannot_be_converted_to_a_personal_draft(self):
        self.page.locator('#demoBtn').click()
        self.assertIn('DÉMONSTRATION FICTIVE',self.page.locator('#mirrorResult').inner_text())
        self.page.locator('[data-step-jump="0"]').click()
        self.assertTrue(self.page.locator('#nameA').is_disabled())
        self.go('premium')
        self.page.locator('#premiumSource').select_option('mirror')
        self.assertEqual(self.page.locator('#premiumPersonA option').count(),0)

    def test_viewing_a_demo_preserves_the_personal_draft_on_disk(self):
        original={'draft':{'nameA':'Lina','nameB':'Noé'},'mirrors':[],'memories':[],'checkins':[]}
        self.page.evaluate("data=>localStorage.setItem('origin_vivant_local_v1',JSON.stringify(data))",original)
        self.page.reload();before=self.page.evaluate("localStorage.getItem('origin_vivant_local_v1')")
        self.page.locator('#demoBtn').click()
        self.page.locator('[data-step-jump="4"]').click()
        self.page.locator('#saveMirror').click()
        self.assertEqual(self.page.evaluate("localStorage.getItem('origin_vivant_local_v1')"),before)

    def test_a_stale_tab_cannot_overwrite_another_tab_and_can_export_its_work(self):
        other=self.context.new_page();other.goto(BASE+'/vivant/')
        newer={'draft':{'nameA':'Copie récente'},'mirrors':[],'memories':[],'checkins':[]}
        other.evaluate("data=>localStorage.setItem('origin_vivant_local_v1',JSON.stringify(data))",newer)
        self.go('miroir');self.page.locator('#nameA').fill('Mon travail local')
        self.assertIn('Sauvegarde interrompue',self.page.locator('#toast').inner_text())
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('origin_vivant_local_v1')).draft.nameA"),'Copie récente')
        self.go('carnet')
        with self.page.expect_download() as download:self.page.locator('#exportJson').click()
        saved=json.loads(Path(download.value.path()).read_text())
        self.assertEqual(saved['carnet']['draft']['nameA'],'Mon travail local')

    def test_malformed_local_backup_is_not_overwritten_and_can_be_rescued(self):
        raw='{"draft":{},"memories":"format inconnu à préserver"}'
        self.page.evaluate("raw=>localStorage.setItem('origin_vivant_local_v1',raw)",raw)
        self.page.reload();self.go('miroir');self.page.locator('#nameA').fill('Camille')
        self.assertEqual(self.page.evaluate("localStorage.getItem('origin_vivant_local_v1')"),raw)
        self.go('carnet')
        with self.page.expect_download() as download:self.page.locator('#exportJson').click()
        recovered=json.loads(Path(download.value.path()).read_text())
        self.assertEqual(recovered['format'],'origin-local-recovery-1');self.assertEqual(recovered['carnet_raw'],raw)

    def test_tree_creation_and_consent_handoff_to_real_demo_render(self):
        self.page.goto(BASE+'/vivant/arbre-vivant.html')
        self.page.on('dialog',lambda dialog:dialog.accept())
        self.page.locator('#btnStart').click()
        self.page.locator('#personName').fill('Lina')
        self.page.locator('#birthDate').fill('1990-05-12')
        self.page.locator('#submitPerson').click()
        self.assertIn('1 personne',self.page.locator('#summary').inner_text())
        self.page.goto(BASE+'/vivant/')
        self.go('premium')
        self.assertEqual(self.page.locator('#premiumPersonA option').count(),1)
        self.page.locator('#premiumDemo').click()
        self.assertIn('Confirme ton choix',self.page.locator('#premiumStatus').inner_text())
        self.page.locator('#premiumConsent').check()
        self.page.locator('#premiumDemo').click()
        self.page.wait_for_url('**/premium-demo/')
        self.assertEqual(self.page.locator('#prenom1').input_value(),'Lina')
        self.assertEqual(self.page.locator('#date_naissance1').input_value(),'1990-05-12')
        self.assertEqual(self.page.locator('#genre1').input_value(),'')
        self.assertEqual(self.page.locator('#ville1').input_value(),'')
        self.assertIsNone(self.page.evaluate("sessionStorage.getItem('origin_premium_handoff_v1')"))
        self.page.locator('#genre1').select_option('Femme')
        self.page.locator('#ville1').select_option('paris')
        self.page.locator('button[type=submit]').click()
        self.page.wait_for_url('**/demo/generate')
        self.assertIn('Aucun email envoyé',self.page.locator('body').inner_text())
        self.assertEqual(self.page.get_by_role('link',name='Ouvrir le PDF').count(),1)

    def test_account_login_and_voluntary_encrypted_restore_in_browser(self):
        email='browser-'+secrets.token_hex(6)+'@example.invalid'
        password=secrets.token_urlsafe(24)
        hashed=docker('exec','-i',PHP,'php','-r','echo password_hash(stream_get_contents(STDIN), PASSWORD_DEFAULT);',input=password)
        sql(f"INSERT INTO users(email,password_hash,verified_at,privacy_version,privacy_accepted_at,created_at) VALUES('{email}','{hashed}',UTC_TIMESTAMP(),'test',UTC_TIMESTAMP(),UTC_TIMESTAMP());")
        self.page.on('dialog',lambda dialog:dialog.accept())
        original={'draft':{'nameA':'Lina'},'mirrors':[],'memories':[{'text':'Un souvenir de test'}],'checkins':[], 'pages':[{'id':'page-fiction','subject':'gratitude','text':'Page entièrement fictive pour la sauvegarde de test.','at':'2026-10-23T08:00:00Z'}]}
        family={'demo':False,'people':[{'id':'a','name':'Lina','parents':[],'partners':[]}], 'selected':'a','anchor':'a'}
        self.page.evaluate("data => {localStorage.setItem('origin_vivant_local_v1',JSON.stringify(data[0]));localStorage.setItem('origin_arbre_vivant_v1',JSON.stringify(data[1]));}",[original,family])
        self.page.reload()
        self.page.locator('[data-account=login]').click()
        self.page.locator('#accountEmail').fill(email)
        self.page.locator('#accountPassword').fill(password)
        with self.page.expect_response(lambda r:'op=login' in r.url) as login:
            self.page.locator('#accountSubmit').click()
        self.assertEqual(login.value.status,200)
        with self.page.expect_response(lambda r:'op=save' in r.url) as saved:
            self.page.locator('[data-account=save]').click()
        self.assertEqual(saved.value.status,200)
        self.page.evaluate("localStorage.setItem('origin_vivant_local_v1',JSON.stringify({draft:{},mirrors:[],memories:[],checkins:[]}))")
        with self.page.expect_navigation():
            self.page.locator('[data-account=load]').click()
        restored=self.page.evaluate("JSON.parse(localStorage.getItem('origin_vivant_local_v1'))")
        self.assertEqual(restored['memories'][0]['text'],'Un souvenir de test')
        self.assertEqual(restored['pages'],original['pages'])
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('origin_arbre_vivant_v1')).people[0].name"),'Lina')
        with self.page.expect_response(lambda r:'op=logout' in r.url) as logout:
            self.page.locator('[data-account=logout]').click()
        self.assertEqual(logout.value.status,200)


if __name__=='__main__':
    unittest.main(verbosity=2)
