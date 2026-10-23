"""Version HTML autonome de l'aperçu fictif, sans serveur ni StackBlitz.

Réutilise les pages déjà isolées de web-preview/. Les sources commerciales
restent intactes. L'Arbre s'ouvre dans un document intégré de même origine.
"""
import base64
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'web-preview'
OUTPUT = DIRECTORY / 'ORIGIN_DEMO.html'


def inline_page(name, directory):
    text = (directory / name).read_text()
    text = re.sub(
        r'<link rel="stylesheet" href="([\w.-]+)">',
        lambda match: '<style>' + (directory / match[1]).read_text() + '</style>', text)

    def script(match):
        code = (directory / match[1]).read_text()
        if match[1] == 'preview-fixtures.js':
            code = code.replace(
                "history.replaceState(null,'',new URL('./#accueil',location.href));location.reload();",
                "window.parent.postMessage({type:'origin-portable-reset'},'*');")
        if match[1] == 'origin-vivant.js':
            # Certains lecteurs injectent une <base> distante. La navigation
            # reste relative à la page ouverte, sans toucher au script source.
            code = code.replace("window.history.pushState(null,'','#'+where)",
                                "window.history.pushState(null,'',location.href.split('#')[0]+'#'+where)")
        return '<script>' + code.replace('</script', '<\\/script') + '</script>'

    text = re.sub(r'<script src="([\w.-]+)"(?: defer)?></script>', script, text)
    image = logo_uri(directory)
    # Une seule copie de l'emblème, partagé avec l'Arbre intégré : éviter
    # plusieurs Mo de base64 répété dans un téléchargement mobile.
    for attribute in ('src', 'href'):
        for value in ('logo-origin-officiel.png', image):
            text = text.replace(attribute+'="'+value+'"', 'data-portable-logo=""')
    text = text.replace('<head>', '''<head><script>
document.addEventListener('DOMContentLoaded',()=>{
  const image=window.ORIGIN_PORTABLE_LOGO||parent.ORIGIN_PORTABLE_LOGO;
  document.querySelectorAll('[data-portable-logo]').forEach(node=>{
    node.setAttribute(node.tagName==='LINK'?'href':'src',image);
  });
});
</script>''', 1)
    # Ce fichier utilise son propre espace de démonstration.
    text = text.replace('origin_web_preview_', 'origin_portable_preview_')
    return text


def logo_uri(directory):
    return 'data:image/png;base64,' + base64.b64encode(
        (directory / 'logo-origin-officiel.png').read_bytes()).decode()


def build(directory=DIRECTORY):
    tree = inline_page('arbre-vivant.html', directory)
    tree = tree.replace(
        'OriginProfiles.route(location.hash);',
        "OriginProfiles.route(window.ORIGIN_PORTABLE_TREE_HASH||'');")
    tree_bridge = '''<script>
document.addEventListener('click',event=>{
  const link=event.target.closest('a[href]');
  const href=link?.getAttribute('href');
  if(!href?.startsWith('./#'))return;
  event.preventDefault();
  parent.postMessage({type:'origin-portable-navigate',hash:href.slice(2)},'*');
});
</script>'''
    tree = tree.replace('</body>', tree_bridge + '</body>')
    page = inline_page('index.html', directory)
    page = page.replace('<head>', '<head><script>window.ORIGIN_PORTABLE_LOGO=' +
                        json.dumps(logo_uri(directory)) + ';</script>', 1)
    page = re.sub(r'(<a\b[^>]*)(href="arbre-vivant\.html[^\"]*")',
                  r'\1data-portable-tree="" \2', page)
    # srcdoc garde la même origine et le même stockage local que le document.
    page = page.replace("connect-src 'none';", "connect-src 'none'; frame-src 'self';")
    template = json.dumps(tree, ensure_ascii=False).replace('<', '\\u003c')
    bridge = '''
<style>
#portableTree{position:fixed;inset:0;margin:0;border:0;padding:0;width:100%;max-width:none;height:100dvh;max-height:none;background:#11110e;color:#f7edda}
#portableTree[open]{display:flex;flex-direction:column}
#portableTree .portable-toolbar{display:flex;align-items:center;justify-content:space-between;gap:10px;padding:8px 14px;font:14px system-ui;background:#1c1911;border-bottom:1px solid #76643d}
#portableTree button{padding:8px 14px;color:#f7edda;background:#31291a;border:1px solid #bfa15f;border-radius:8px}
#portableTree iframe{flex:1;width:100%;min-height:0;border:0}
</style>
<dialog id="portableTree" aria-label="Arbre vivant fictif">
<div class="portable-toolbar"><span>Arbre vivant · Démonstration</span><button type="button" id="portableTreeClose">← Retour</button></div>
<iframe id="portableTreeFrame" title="Arbre vivant : profils entièrement fictifs"></iframe>
</dialog>
<script>
(() => {
  const treeDocument=__TREE_DOCUMENT__;
  const dialog=document.getElementById('portableTree');
  const frame=document.getElementById('portableTreeFrame');
  const refresh=()=>window.dispatchEvent(new Event('storage'));
  dialog.addEventListener('close',refresh);
  document.getElementById('portableTreeClose').addEventListener('click',()=>dialog.close());
  document.addEventListener('click',event=>{
    const link=event.target.closest('a[href]');
    const href=link?.getAttribute('href');
    if(!link?.hasAttribute('data-portable-tree')&&!href?.startsWith('arbre-vivant.html'))return;
    event.preventDefault();
    const hash=href.includes('#')?href.slice(href.indexOf('#')):'';
    const prelude='<scr'+'ipt>window.ORIGIN_PORTABLE_TREE_HASH='+JSON.stringify(hash).replaceAll('<','\\\\u003c')+';<'+ '/script>';
    frame.srcdoc=treeDocument.replace('<head>','<head>'+prelude);
    dialog.showModal();
  });
  window.addEventListener('message',event=>{
    if(event.source!==window&&event.source!==frame.contentWindow)return;
    if(event.data?.type==='origin-portable-reset'){
      if(dialog.open)dialog.close();
      history.replaceState(null,'',location.href.split('#')[0]+'#accueil');
      location.reload();
    }
    if(event.source!==frame.contentWindow||event.data?.type!=='origin-portable-navigate')return;
    if(typeof event.data.hash!=='string'||!/^#(?:accueil|miroir|arbre|carnet|constellation(?:-demo)?|parcours)(?:\\/[^\\s]*)?$/.test(event.data.hash))return;
    dialog.close();refresh();
    location.hash=event.data.hash;
  });
})();
</script>'''.replace('__TREE_DOCUMENT__', template)
    page = page.replace('</body>', bridge + '</body>')
    output = directory / OUTPUT.name
    output.write_text(page)
    return output


if __name__ == '__main__':
    print('Démonstration HTML autonome :', build())
