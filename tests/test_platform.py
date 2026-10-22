import ast
import hashlib
import json
from pathlib import Path
import unittest
from copy import deepcopy

from platform_demo import create_app
from demo_support import OfflineHTML
from unittest.mock import patch
from test_origin import OfflineTest
import app as engine


ROOT = Path(__file__).resolve().parents[1]


class PreservationTests(unittest.TestCase):
    def test_all_non_security_engine_logic_and_prompts_are_preserved(self):
        proof = json.loads((ROOT / 'fixtures/security-engine-preservation.json').read_text())
        module = ast.parse((ROOT / 'app.py').read_text())
        webhook = next(n for n in module.body if isinstance(n, ast.FunctionDef) and n.name == 'webhook')
        worker = next(n for n in ast.walk(webhook) if isinstance(n, ast.FunctionDef) and n.name == 'generer')
        self.assertEqual(hashlib.sha256(ast.dump(worker, include_attributes=False).encode()).hexdigest(), proof['generation_worker_sha256'])
        module.body = [n for n in module.body
            if not (isinstance(n, ast.FunctionDef) and n.name in proof['authorized_security_functions'])
            and not (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_CODES_SECRET' for t in n.targets))
            and not (isinstance(n, ast.ImportFrom) and n.module == 'premium_security')]
        digest = hashlib.sha256(ast.dump(module, include_attributes=False).encode()).hexdigest()
        self.assertEqual(digest, proof['protected_module_sha256'])

    def test_original_dependencies_and_assets_are_unchanged(self):
        proof = json.loads((ROOT / 'fixtures/engine-preservation.json').read_text())
        for name, expected in proof['original_files'].items():
            with self.subTest(file=name):
                self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)


class PlatformTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_original_pack_is_available_with_local_demo_capability(self):
        result = self.client.get('/vivant/')
        self.assertEqual(result.status_code, 200)
        self.assertIn('Le Miroir', result.text)
        self.assertIn('ORIGIN PREMIUM', result.text)
        self.assertIn('origin-demo-premium', result.text)
        self.assertEqual(self.client.get('/premium-demo/').status_code, 200)

    def test_php_source_and_personal_files_are_never_served(self):
        for path in ('api/bootstrap.php', 'api/schema.sql', '.htaccess', '../app.py', 'origin-vivant-config.php'):
            with self.subTest(path=path):
                self.assertEqual(self.client.get('/vivant/' + path).status_code, 404)

    def test_unconfigured_api_is_reported_without_fabricated_account(self):
        result = self.client.get('/vivant/api/?op=status')
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json['code'], 'not_configured')

    def test_facade_cannot_connect_to_production(self):
        for url in ('https://origin-famille.fr/vivant/api/', 'http://example.com/', 'http://user@localhost/', 'file:///etc/passwd'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                create_app(url)


class OtherBookletRenderTests(OfflineTest):
    def test_existing_family_prestige_birth_and_vocation_personalized_renders(self):
        clients=[{'prenom':'Lina','nom':'Exemple','jour':12,'mois':5,'annee':1990,'ville':'Paris','genre':'Femme'},
                 {'prenom':'Noé','nom':'Exemple','jour':23,'mois':9,'annee':1988,'ville':'Lyon','genre':'Homme'}]
        base=json.loads((ROOT/'fixtures/demo_narrative.json').read_text())
        astros=[engine.fmt_profil(client)[2] for client in clients]
        for offer,kind,count in [('famille','adulte',2),('prestige','adulte',2),('solo','naissance',1),('vocation','adulte',1)]:
            with self.subTest(offer=offer,type_analyse=kind):
                narrative=deepcopy(base)
                titles=['Architecture intérieure','Le travail au quotidien',"Territoires d’expression",'Pistes professionnelles','Périodes charnières','Tes prochains pas'] if offer=='vocation' else [f'Une invitation {i+1}' for i in range(10)]
                narrative['sections']=[{**deepcopy(base['sections'][i%5]),'titre':title} for i,title in enumerate(titles)]
                narrative['profil_contribution']='<p>Un exemple de contribution à explorer.</p>'
                narrative['questions_decision']='<p>Quelle première étape souhaites-tu essayer ?</p>'
                narrative['mantras']=[{'prenom':client['prenom'],'texte':'Un pas après l’autre.','note':f"Exemple : chemin de vie {engine.chemin_de_vie(client['jour'],client['mois'],client['annee'])}."} for client in clients[:count]]
                narrative['mantras'].append({'prenom':'Ensemble','texte':'Un exemple de lien.','note':''})
                engine._valider_narratif_client(offer,narrative,clients[:count],kind)
                document=engine.generer_html(offer,clients[:count],narrative,astros[:count],kind)
                self.assertIn('Lina',document)
                if count==2:self.assertIn('Noé',document)
                with patch.object(engine,'WeasyprintHTML',OfflineHTML):
                    pdf=engine.generer_pdf_imprimable(offer,clients[:count],narrative,astros[:count],kind)
                self.assertTrue(pdf.startswith(b'%PDF-'))
                self.assertGreater(len(pdf),10000)


if __name__ == '__main__':
    unittest.main()
