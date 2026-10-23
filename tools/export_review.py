"""Archive de revue issue exclusivement des fichiers Git du commit courant.

Jamais de parcours des dossiers runtime, de lecture des .env ou d'historique Git.
Usage : python tools/export_review.py /workspace/exports
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git','-C',str(ROOT),*args])


def export(destination):
    if git('status','--porcelain').strip():raise RuntimeError('Committer le dossier avant export.')
    commit=git('rev-parse','HEAD').decode().strip()
    tree=git('ls-tree','-r','-z',commit).decode().split('\0')
    entries=[]
    patterns=[r'(?:sk|rk)_(?:test|live)_[A-Za-z0-9]{16,}',r'whsec_[A-Za-z0-9]{20,}',
              r'sk-ant-[A-Za-z0-9_-]{20,}',r'gh[pousr]_[A-Za-z0-9]{25,}',
              r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']
    denied={'.git','.venv','node_modules','attachments','.cache','.setup','__pycache__'}
    for row in filter(None,tree):
        meta,name=row.split('\t',1);mode,kind,oid=meta.split(' ')
        p=PurePosixPath(name)
        if kind!='blob' or mode=='120000' or p.is_absolute() or '..' in p.parts or denied.intersection(p.parts):raise RuntimeError('Chemin interdit dans la revue : '+name)
        if (p.name.startswith('.env') and p.name!='.env.example') or p.name=='origin-vivant-config.php' or p.suffix in {'.sqlite','.sqlite3','.db','.log','.csv'}:raise RuntimeError('Fichier privé/runtime interdit : '+name)
        data=git('cat-file','blob',oid);decoded=data.decode('utf-8',errors='ignore')
        if any(re.search(pattern,decoded) for pattern in patterns):raise RuntimeError('Motif de secret détecté (valeur masquée) dans : '+name)
        if p.suffix=='.sql' and re.search(r'^\s*(?:INSERT\s+INTO|REPLACE\s+INTO|LOAD\s+DATA)',decoded,re.I|re.M):raise RuntimeError('Données SQL interdites : '+name)
        entries.append((name,data,int(mode,8)))
    now=datetime.now(timezone.utc)
    manifest={'commit':commit,'created_at':now.isoformat(),'files':[{'path':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()} for name,data,mode in entries]}
    security={'source':'Blobs Git du commit courant uniquement ; aucun historique ni fichier runtime.',
        'tracked_files':len(entries),'credential_patterns_detected':0,'sql_data_statements_detected':False,
        'personal_runtime_records_exported':False,'demo_outputs':'Personnes et textes fictifs, PDF explicitement marqués DÉMONSTRATION.',
        'limits':'Recherche de motifs et périmètre Git contrôlé ; ne constitue pas une certification exhaustive.'}
    destination.mkdir(parents=True,exist_ok=True)
    path=destination/f'ORIGIN_AUDIT_CLAUDE_{commit[:7]}.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for name,data,mode in entries:
            info=zipfile.ZipInfo('origin-serveur/'+name,now.timetuple()[:6]);info.external_attr=mode<<16;info.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(info,data)
        for name,payload in [('EXPORT_MANIFEST.json',manifest),('EXPORT_SECURITY.json',security)]:
            z.writestr('origin-serveur/review/final-2026-10-23/'+name,json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for name,data,mode in entries:assert z.read('origin-serveur/'+name)==data
    path.with_suffix('.zip.sha256').write_text(digest+'  '+path.name+'\n')
    print(json.dumps({'zip':str(path),'bytes':path.stat().st_size,'sha256':digest,'files':len(entries)+2},ensure_ascii=False))


if __name__=='__main__':export(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT.parent/'exports')
