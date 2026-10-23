"""Aperçu statique des sources actuelles : fiction, stockage isolé, sans backend.

Usage : python3 tools/vivant/build_web_preview.py
La sortie web-preview/ est la seule arborescence à héberger pour cet aperçu.
"""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'hostinger/vivant'
OUTPUT = ROOT / 'web-preview'
FILES = ('index.html', 'arbre-vivant.html', 'origin-vivant.js',
         'origin-profiles.js', 'origin-storage.js', 'origin-integration.js',
         'origin-vivant.css', 'logo-origin-officiel.png')
KEYS = {
    'origin_vivant_local_v1': 'origin_web_preview_carnet_v1',
    'origin_arbre_vivant_v1': 'origin_web_preview_tree_v1',
    'origin_restore_recovery_v1': 'origin_web_preview_recovery_v1',
    'origin_premium_handoff_v1': 'origin_web_preview_handoff_v1',
}
CSP = ("default-src 'self'; script-src 'self' 'unsafe-inline'; "
       "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
       "font-src 'self' data:; connect-src 'none'; form-action 'none'; "
       "base-uri 'none'; object-src 'none'")
BANNER = '''<aside class="preview-banner" aria-label="Démonstration fictive">
<div><strong>ORIGIN RÉVOLUTION · APERÇU WEB</strong>
<span>Personnages fictifs · Aucun compte, paiement ou envoi réel. Utilise uniquement des exemples inventés.</span></div>
<button type="button" id="previewReset">Recommencer la démonstration</button>
</aside>'''


def build(output=OUTPUT):
    output.mkdir(parents=True, exist_ok=True)
    expected = set(FILES) | {'preview-fixtures.js', 'preview.css', 'preview-server.cjs', 'package.json', '.nojekyll', 'manifest.json'}
    if any(p.name not in expected or not p.is_file() for p in output.iterdir()):
        raise RuntimeError('La sortie contient des fichiers inconnus : les préserver avant de reconstruire.')
    provenance = {}
    for name in FILES:
        data = (SOURCE / name).read_bytes()
        provenance[name] = hashlib.sha256(data).hexdigest()
        if name.endswith(('.html', '.js', '.css')):
            text = data.decode('utf-8')
            for before, after in KEYS.items():
                text = text.replace(before, after)
            if name.endswith('.html'):
                text = re.sub(r'<script\s+src="origin-commercial\.js"\s+defer></script>\s*', '', text)
                text = re.sub(r'href="https://origin-famille\.fr[^" ]*"', 'href="./#accueil"', text)
                text = text.replace('aria-label="ORIGIN, visiter le site officiel"', 'aria-label="Accueil de la démonstration ORIGIN"')
                text = text.replace('aria-label="Accueil ORIGIN"', 'aria-label="Accueil de la démonstration ORIGIN"')
                text = text.replace('origin-famille.fr ↗', 'Retour à la démonstration')
                text = text.replace('PROTOTYPE LOCAL · DONNÉES SUR CET APPAREIL', 'DÉMONSTRATION · DONNÉES FICTIVES')
                text = text.replace('<head>', '<head>\n<meta name="robots" content="noindex, nofollow, noarchive">\n'
                    '<meta http-equiv="Content-Security-Policy" content="'+CSP+'">\n'
                    '<link rel="stylesheet" href="preview.css">\n'
                    '<script src="preview-fixtures.js"></script>', 1)
                text = text.replace('<body>', '<body>\n'+BANNER, 1)
            data = text.encode('utf-8')
        (output / name).write_bytes(data)
    for name in ['preview-fixtures.js', 'preview.css', 'preview-server.cjs', 'package.json']:
        shutil.copyfile(ROOT / 'tools/vivant/preview' / name, output / name)
    (output / '.nojekyll').write_text('')
    manifest = {
        'kind': 'origin-fictional-web-preview', 'source_branch': 'preview/origin-revolution',
        'source_commit_at_build': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256': provenance, 'storage_keys': KEYS,
        'payments': False, 'accounts': False, 'external_api_calls': False,
        'personal_client_data': False, 'commercial_server_sources_included': False,
        'static_preview_server_included': True,
        'files': {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir()) if p.name != 'manifest.json'},
    }
    (output / 'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    return output


if __name__ == '__main__':
    print('Aperçu statique préparé :', build())
