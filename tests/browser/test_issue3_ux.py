"""Issue #3 : données entièrement fictives, pas d'API ou de famille réelle."""
import json
import os
from pathlib import Path
import time
import unittest
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[2]
BASE=os.environ.get('ORIGIN_BROWSER_URL','http://127.0.0.1:5080')
SHOTS=ROOT/'review/issue-3/screenshots'
CARNET='origin_vivant_local_v1'
TREE='origin_arbre_vivant_v1'


def notebook(**extra):
    return {'draft':{},'mirrors':[],'memories':[],'checkins':[],**extra}


def family():
    return {'demo':False,'selected':'a','anchor':'a','people':[
        {'id':'parent','name':'Claude Exemple','birth':'1960-03-12','parents':[],'partners':[]},
        {'id':'a','name':'Lina Exemple','birth':'1990-05-12','parents':['parent'],'partners':['partner']},
        {'id':'b','name':'Noé Exemple','birth':'1992-09-23','parents':['parent'],'partners':[]},
        {'id':'partner','name':'Alex Exemple','birth':'1988-09-23','parents':[],'partners':['a']},
        {'id':'other','name':'Sam Exemple','birth':'1989-06-01','parents':[],'partners':[]},
    ]}


class Issue3UxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if urlparse(BASE).hostname not in ('127.0.0.1','localhost'):
            raise ValueError('Tests réservés au serveur local')
        cls.playwright=sync_playwright().start()
        cls.browser=cls.playwright.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        SHOTS.mkdir(parents=True,exist_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close();cls.playwright.stop()

    def setUp(self):
        self.context=self.browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce')
        self.addCleanup(self.context.close)
        self.page=self.context.new_page();self.errors=[];self.external=[]
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        def guard(route):
            if urlparse(route.request.url).netloc!=urlparse(BASE).netloc:
                self.external.append(route.request.url);route.abort()
            else:route.continue_()
        self.page.route('**/*',guard);self.page.goto(BASE+'/vivant/')

    def tearDown(self):
        self.assertEqual(self.errors,[]);self.assertEqual(self.external,[])

    def seed(self,tree=None,carnet=None):
        self.page.evaluate("data=>{if(data.tree)localStorage.setItem('origin_arbre_vivant_v1',JSON.stringify(data.tree));if(data.carnet)localStorage.setItem('origin_vivant_local_v1',JSON.stringify(data.carnet));}",{'tree':tree,'carnet':carnet})
        self.page.reload()

    def go(self,view):
        self.page.locator(f'.nav-item[data-go="{view}"]').click()

    def stored(self):
        return self.page.evaluate("JSON.parse(localStorage.getItem('origin_vivant_local_v1'))")

    def test_mobile_write_reload_edit_and_confirmed_delete_with_keyboard(self):
        start=time.monotonic();self.go('carnet')
        self.page.locator('#writePage').focus();self.page.keyboard.press('Enter')
        self.assertTrue(self.page.locator('#pageText').evaluate('(el)=>el===document.activeElement'))
        self.page.locator('#pageSubject').select_option('gratitude')
        self.page.locator('#pageText').fill('Donnée fictive : merci pour ce moment partagé.')
        self.page.keyboard.press('Tab');self.page.keyboard.press('Enter')
        self.assertLess(time.monotonic()-start,60)
        self.assertEqual(len(self.stored()['pages']),1)
        self.page.reload();self.assertTrue(self.page.locator('#view-carnet').is_visible())
        self.assertIn('merci',self.page.locator('#pageList').inner_text())
        self.page.locator('[data-page-edit]').click();self.page.locator('#pageText').fill('Donnée fictive : une page relue et modifiée.')
        self.page.locator('#savePage').click()
        self.assertEqual(self.stored()['pages'][0]['text'],'Donnée fictive : une page relue et modifiée.')
        self.page.screenshot(path=str(SHOTS/'carnet-mobile.png'),full_page=True)
        self.page.once('dialog',lambda d:d.dismiss());self.page.locator('[data-page-delete]').click()
        self.assertEqual(len(self.stored()['pages']),1)
        self.page.once('dialog',lambda d:d.accept());self.page.locator('[data-page-delete]').click()
        self.assertEqual(self.stored()['pages'],[])

    def test_legacy_notebook_archives_and_json_text_exports_include_written_pages(self):
        original=notebook(mirrors=[{'id':'m','at':'2026-01-01T12:00:00Z','nameA':'Lina Exemple','nameB':'Sam Exemple'}],memories=[{'id':'s','at':'2026-01-01T12:00:00Z','text':'Souvenir fictif.'}],checkins=[{'id':'b','at':'2026-01-01T12:00:00Z','day':'2026-01-01','mood':3,'note':'Bilan fictif.'}])
        original['legacyMetadata']='Métadonnée fictive à préserver.';original['mirrors'][0]['legacyContext']='Contexte fictif.'
        self.seed(carnet=original);self.go('carnet')
        self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Ma nouvelle page fictive.');self.page.locator('#savePage').click()
        saved=self.stored();self.assertEqual([len(saved[k]) for k in ['mirrors','memories','checkins','pages']],[1,1,1,1])
        self.assertEqual(saved['legacyMetadata'],original['legacyMetadata']);self.assertEqual(saved['mirrors'][0]['legacyContext'],'Contexte fictif.')
        self.assertIn('PAGE RÉDIGÉE',self.page.locator('#pageList').inner_text());self.assertIn('MIROIR',self.page.locator('#historyList').inner_text())
        with self.page.expect_download() as download:self.page.locator('#exportJson').click()
        data=json.loads(Path(download.value.path()).read_text());self.assertEqual(data['carnet']['pages'],saved['pages'])
        with self.page.expect_download() as download:self.page.locator('#exportText').click()
        self.assertIn('Ma nouvelle page fictive.',Path(download.value.path()).read_text())
        self.page.evaluate("localStorage.removeItem('origin_vivant_local_v1')");self.page.reload();self.go('carnet')
        self.assertEqual(self.page.locator('.page-record').count(),0)
        self.page.once('dialog',lambda d:d.accept())
        self.page.locator('#importJson').set_input_files({'name':'copie-fictive.json','mimeType':'application/json','buffer':json.dumps(data).encode()})
        self.page.wait_for_function("document.getElementById('pageStatus').textContent.includes('importée')");self.page.reload();self.go('carnet')
        self.assertIn('Ma nouvelle page fictive.',self.page.locator('#pageList').inner_text())

    def test_storage_error_keeps_the_text_and_reports_no_false_success(self):
        self.seed(carnet=notebook());self.go('carnet');before=self.page.evaluate(f'localStorage.getItem("{CARNET}")')
        self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Texte fictif à conserver si le quota échoue.')
        self.page.evaluate("() => {const set=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='origin_vivant_local_v1')throw new DOMException('Quota','QuotaExceededError');return set.call(this,k,v)}}")
        self.page.locator('#savePage').click()
        self.assertIn('non enregistrée',self.page.locator('#pageStatus').inner_text())
        self.assertIn('conserver',self.page.locator('#pageText').input_value())
        self.assertEqual(self.page.evaluate(f'localStorage.getItem("{CARNET}")'),before)

    def test_reopening_an_edited_page_and_cancel_do_not_lose_unsaved_text(self):
        self.seed(carnet=notebook(pages=[{'id':'p','subject':'libre','text':'Page fictive enregistrée.','at':'2026-10-23T08:00:00Z'}]))
        self.go('carnet');self.page.locator('[data-page-edit]').click();self.page.locator('#pageText').fill('Modification fictive encore non enregistrée.')
        self.page.locator('[data-page-edit]').click()
        self.assertEqual(self.page.locator('#pageText').input_value(),'Modification fictive encore non enregistrée.')
        self.page.once('dialog',lambda d:d.dismiss());self.page.locator('#cancelPage').click()
        self.assertTrue(self.page.locator('#pageForm').is_visible())
        self.assertEqual(self.stored()['pages'][0]['text'],'Page fictive enregistrée.')
        self.page.once('dialog',lambda d:d.accept());self.page.locator('#cancelPage').click()
        self.assertFalse(self.page.locator('#pageForm').is_visible())

    def test_invalid_page_data_is_preserved_and_not_silently_reset(self):
        bad=notebook(pages=[{'id':'future','subject':'future','text':'Copie fictive inconnue.'}])
        self.seed(carnet=bad);before=self.page.evaluate(f'localStorage.getItem("{CARNET}")')
        self.go('carnet');self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Nouveau texte fictif.')
        self.page.locator('#savePage').click()
        self.assertEqual(self.page.evaluate(f'localStorage.getItem("{CARNET}")'),before)
        self.assertEqual(self.page.locator('#pageStatus').get_attribute('data-error'),'true')

    def test_stale_tab_cannot_replace_a_newer_page(self):
        self.seed(carnet=notebook());self.go('carnet');self.page.locator('#writePage').click();self.page.locator('#pageText').fill('Travail fictif dans un onglet périmé.')
        other=self.context.new_page();other.goto(BASE+'/vivant/')
        newer=notebook(pages=[{'id':'new','subject':'question','text':'Page fictive récente.','at':'2026-10-23T12:00:00Z'}])
        other.evaluate("data=>localStorage.setItem('origin_vivant_local_v1',JSON.stringify(data))",newer)
        self.page.locator('#savePage').click()
        self.assertEqual(self.stored(),newer);self.assertIn('périmé',self.page.locator('#pageText').input_value())
        self.assertIn('non enregistrée',self.page.locator('#pageStatus').inner_text())

    def test_every_tree_profile_opens_constellation_preselected(self):
        self.seed(tree=family())
        for person in family()['people']:
            self.page.goto(BASE+'/vivant/arbre-vivant.html')
            self.page.locator(f'.tree-card[data-id="{person["id"]}"]').click()
            if person['id']=='a':self.page.screenshot(path=str(SHOTS/'arbre-fiche-mobile.png'),full_page=True)
            self.page.locator('#profileConstellation').click()
            self.page.wait_for_url('**/#constellation/'+person['id'])
            self.assertEqual(self.page.locator('#constellationPersonA').input_value(),person['id'])
            self.assertTrue(self.page.locator('#view-constellation').is_visible())

    def test_relations_and_no_duplicate_selection_with_manual_correction(self):
        self.seed(tree=family());self.go('constellation')
        self.page.locator('#constellationPersonA').select_option('a')
        for selected,label in [('parent','parent'),('b','Fratrie'),('partner','Partenaires'),('other','Autre lien')]:
            self.page.locator('#constellationPersonB').select_option(selected)
            self.assertIn(label,self.page.locator('#constellationLink').inner_text())
        self.assertTrue(self.page.locator('#constellationPersonB option[value="a"]').evaluate('(option)=>option.disabled'))
        self.page.locator('#constellationRelation').select_option('siblings')
        self.assertIn('Fratrie',self.page.locator('#constellationLink').inner_text())
        self.assertIn('n’a pas été modifié',self.page.locator('#constellationResult').inner_text())
        self.page.reload();self.assertEqual(self.page.locator('#constellationRelation').input_value(),'siblings')

    def test_other_selection_survives_handoff_and_tree_edits_refresh_mirror(self):
        self.seed(tree=family());self.go('constellation')
        self.page.locator('#constellationPersonA').select_option('a');self.page.locator('#constellationPersonB').select_option('other')
        self.page.goto(BASE+'/vivant/arbre-vivant.html')
        self.page.locator('.tree-card[data-id="b"]').click();self.page.locator('#profileConstellation').click()
        self.page.locator('#view-constellation').wait_for(state='visible')
        self.assertEqual(self.page.locator('#constellationPersonB').input_value(),'other')
        self.page.locator('#constellationMirror').click()
        self.assertEqual(self.page.locator('[data-relationship="proche"]').get_attribute('aria-pressed'),'true')
        editor=self.context.new_page();editor.goto(BASE+'/vivant/arbre-vivant.html')
        editor.locator('.tree-card[data-id="b"]').click();editor.locator('#btnEdit').click()
        editor.locator('#personName').fill('Noé Exemple modifié');editor.locator('#birthDate').fill('1993-09-23');editor.locator('#submitPerson').click()
        self.page.wait_for_function("document.getElementById('nameA').value==='Noé Exemple modifié'")
        self.assertEqual(self.page.locator('#birthA').input_value(),'1993-09-23')
        self.go('constellation');self.assertIn('Noé Exemple modifié',self.page.locator('#constellationResult').inner_text())
        self.page.locator('#constellationWrite').click();self.assertTrue(self.page.locator('#pageForm').is_visible())

    def test_shared_mirror_selector_and_manual_override_keep_tree_as_source(self):
        self.seed(tree=family());self.go('miroir')
        self.page.locator('#treePersonB').select_option('other');self.page.locator('#treePersonA').select_option('a');self.page.locator('#useTreePersons').click()
        self.assertEqual(self.page.locator('#birthA').input_value(),'1990-05-12');self.assertEqual(self.stored()['draft']['profileAId'],'a')
        self.assertTrue(self.page.locator('#treePersonB option[value="a"]').evaluate('(option)=>option.disabled'))
        self.page.locator('#nameA').fill('Prénom manuel fictif')
        self.assertEqual(self.stored()['draft']['profileAId'],'')
        other=self.context.new_page();other.goto(BASE+'/vivant/')
        changed=family();changed['people'][1]['name']='Profil Arbre fictif modifié'
        other.evaluate("data=>localStorage.setItem('origin_arbre_vivant_v1',JSON.stringify(data))",changed)
        self.page.wait_for_timeout(100)
        self.assertEqual(self.page.locator('#nameA').input_value(),'Prénom manuel fictif')
        self.assertEqual(self.page.evaluate("JSON.parse(localStorage.getItem('origin_arbre_vivant_v1')).people[1].name"),'Profil Arbre fictif modifié')

    def test_no_tree_demo_manual_and_return_routes_are_explicit(self):
        self.go('constellation');self.assertIn('Aucun arbre personnel',self.page.locator('#constellationSourceStatus').inner_text())
        self.page.locator('#constellationDemo').click();self.assertIn('DÉMONSTRATION FICTIVE',self.page.locator('#constellationSourceStatus').inner_text())
        self.assertIsNone(self.page.evaluate(f'localStorage.getItem("{TREE}")'))
        self.page.locator('#constellationDemo').click();self.page.locator('#constellationSource').select_option('manual')
        self.page.locator('#constellationNameA').fill('Lina Exemple');self.page.locator('#constellationNameB').fill('Sam Exemple')
        self.page.locator('#constellationNameB').blur()
        self.assertIn('Autre lien',self.page.locator('#constellationLink').inner_text())
        self.page.locator('#constellationMirror').click()
        self.assertEqual(self.page.locator('#nameA').input_value(),'Lina Exemple')
        self.go('carnet');self.page.get_by_role('link',name='Retour à mon Arbre').click();self.assertIn('arbre-vivant.html',self.page.url)

    def test_imported_tree_and_corrupt_tree_never_force_a_couple(self):
        self.page.goto(BASE+'/vivant/arbre-vivant.html')
        self.page.once('dialog',lambda d:d.accept());data={'app':'ORIGIN Arbre vivant',**family()}
        self.page.locator('#importFile').set_input_files({'name':'arbre-fictif.json','mimeType':'application/json','buffer':json.dumps(data).encode()})
        self.page.wait_for_function("document.getElementById('summary').textContent.includes('5 personnes')")
        self.page.locator('#profileConstellation').click();self.page.locator('#constellationPersonB').select_option('other')
        self.assertEqual(self.page.locator('#constellationLink').inner_text(),'Autre lien')
        raw='{"demo":false,"people":"format inconnu"}'
        self.page.evaluate("raw=>localStorage.setItem('origin_arbre_vivant_v1',raw)",raw);self.page.reload()
        self.assertIn('illisible',self.page.locator('#constellationSourceStatus').inner_text())
        self.assertEqual(self.page.evaluate(f'localStorage.getItem("{TREE}")'),raw)

    def test_mobile_desktop_layout_and_synthetic_screenshots(self):
        self.seed(tree=family());self.go('constellation');self.page.locator('#constellationPersonB').select_option('other')
        for width in [320,390,768,1440]:
            self.page.set_viewport_size({'width':width,'height':900})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),width+1)
            self.page.mouse.move(0,0)
            if width in [390,1440]:self.page.screenshot(path=str(SHOTS/('constellation-mobile.png' if width==390 else 'constellation-desktop.png')),full_page=True)

    def test_page_text_and_profile_names_are_not_executable_html(self):
        tree=family();tree['people'][1]['name']='<img src=x onerror=window.injected=1>'
        self.seed(tree=tree);self.go('constellation');self.page.locator('#constellationPersonA').select_option('a');self.page.locator('#constellationPersonB').select_option('other')
        self.assertEqual(self.page.locator('#constellationResult img').count(),0)
        self.go('carnet');self.page.locator('#writePage').click();self.page.locator('#pageText').fill('<img src=x onerror=window.injected=1>');self.page.locator('#savePage').click()
        self.assertEqual(self.page.locator('#pageList img').count(),0);self.assertFalse(self.page.evaluate('window.injected===1'))


if __name__=='__main__':unittest.main(verbosity=2)
