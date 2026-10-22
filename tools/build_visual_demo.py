"""Construit une démonstration transportable depuis les composants existants.

Aucun serveur de paiement, aucune clé, aucune requête externe. Ouvrir ensuite
demo-visual/index.html, ou servir ce dossier sur 127.0.0.1 pour l'arbre partagé.
Les PDF sont de vraies sorties du moteur, avec textes et personnes de fixture.
"""
import base64
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from demo import create_app

PACK=ROOT/'hostinger/vivant'
DEST=ROOT/'demo-visual'


def inline_script(name):
    return '<script>\n'+(PACK/name).read_text().replace('</script','<\\/script')+'\n</script>'


def build():
    DEST.mkdir(exist_ok=True)
    logo='data:image/png;base64,'+base64.b64encode((PACK/'logo-origin-officiel.png').read_bytes()).decode()
    page=(PACK/'index.html').read_text()
    page=page.replace('logo-origin-officiel.png',logo)
    page=page.replace('<link rel="stylesheet" href="origin-vivant.css">','<style>'+(PACK/'origin-vivant.css').read_text()+'</style>')
    for name in ['origin-storage.js','origin-vivant.js','origin-integration.js']:
        page=page.replace(f'<script src="{name}" defer></script>',inline_script(name))
    page=page.replace('<script src="origin-commercial.js" defer></script>','')
    page=page.replace('<body>','<body><div style="padding:12px 18px;background:#d5b27b;color:#17110b;text-align:center;overflow-wrap:anywhere"><strong>DÉMONSTRATION · Aucun paiement ni envoi de données</strong><br>Le Miroir et le parcours fonctionnent sur cet appareil. Utilise des profils fictifs.</div>')
    card='''<article class="panel-card"><span class="eyebrow">DÉCOUVRIR LE LIVRET · EXEMPLES FICTIFS</span>
<h2>Du premier échange à une lecture personnelle</h2><p>Le parcours gratuit prépare ton dossier avec ton accord. Ces exemples montrent les rendus existants avec des textes préécrits de démonstration. Ils ne constituent pas une analyse personnalisée payante.</p>
<div class="commit-actions"><a class="btn btn-gold" href="solo-demonstration.pdf" target="_blank" rel="noopener">Voir le PDF Solo</a><a class="btn btn-outline" href="couple-demonstration.pdf" target="_blank" rel="noopener">Voir le PDF Couple</a></div>
<p class="microcopy">Comptes, cloud, Stripe et livraison désactivés dans cette page autonome. Aucun abonnement n’est proposé.</p></article>'''
    page=page.replace('<div class="panel-card premium-draft">',card+'<div class="panel-card premium-draft">')
    page=page.replace('https://origin-famille.fr/','#')
    page=page.replace('<head>','<head><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; img-src data:; style-src \'unsafe-inline\'; script-src \'unsafe-inline\'; connect-src \'none\'; base-uri \'none\'; form-action \'none\'">',1)
    (DEST/'index.html').write_text(page)
    tree=(PACK/'arbre-vivant.html').read_text().replace('<script src="origin-storage.js"></script>',inline_script('origin-storage.js'))
    tree=tree.replace('https://origin-famille.fr/#offres','index.html').replace('https://origin-famille.fr/','index.html')
    (DEST/'arbre-vivant.html').write_text(tree)
    (DEST/'confidentialite.html').write_bytes((PACK/'confidentialite.html').read_bytes())
    people=[{'prenom':'Camille','date_naissance':'1990-05-12','genre':'Femme','ville':'paris'},
            {'prenom':'Alex','date_naissance':'1988-09-23','genre':'Homme','ville':'lyon'}]
    with TemporaryDirectory(prefix='origin-visual-fixtures-') as output:
        client=create_app({'TESTING':True,'DEMO_OUTPUT_DIR':output}).test_client()
        # Même une régression du transport ne peut pas contacter une API.
        with (patch('socket.socket.connect',side_effect=RuntimeError('Réseau interdit pour la démo')),
              patch('socket.getaddrinfo',side_effect=RuntimeError('DNS interdit pour la démo'))):
            for offer,count in [('solo',1),('couple',2)]:
                result=client.post('/demo/generate',json={'offre':offer,'clients':people[:count]})
                if result.status_code!=201:raise RuntimeError('Échec du rendu de démonstration')
                assert result.json['delivered'] is False
                for kind in ['html','pdf']:
                    with client.get(result.json['artifacts'][kind]) as artifact:
                        (DEST/f'{offer}-demonstration.{kind}').write_bytes(artifact.data)
    (DEST/'LIRE_AVANT.txt').write_text('DÉMONSTRATION ORIGIN HORS LIGNE\n\nOuvrir index.html après extraction du ZIP. Aucun compte, API, paiement ou email réel.\nUtiliser des personnages fictifs. Le navigateur peut conserver les saisies sur cet appareil.\nMiroir > Mon parcours > ORIGIN Premium : préparation consentie et exemples PDF Solo/Couple.\nPour une origine commune avec l’arbre et un stockage navigateur prévisible, depuis ce dossier :\n  python -m http.server 8080 --bind 127.0.0.1\n  puis ouvrir http://127.0.0.1:8080\nLes textes des PDF sont des fixtures, les calculs et rendus proviennent du moteur préservé.\nLa personnalisation complète nécessite la démonstration Python locale décrite dans README.md.\n')
    print('Démonstration visuelle construite dans demo-visual/, sans appel réseau.')


if __name__=='__main__':build()
