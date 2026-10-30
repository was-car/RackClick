"""Enable exact592 compatibility only after the real schema10 QA selection."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-593-652'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    receipt=E/'QA-MATRIX-652.json'
    if receipt.exists():raise SystemExit('Preserve existing QA matrix receipt')
    manifest=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json').read_bytes())
    pair={'bundle':manifest['distributions']['frontend']['app.js'],'dll':manifest['distributions']['server']['RackClick.Server.dll']}
    pointer=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes());cfg=json.loads((Path(pointer['directory'])/'manual-qa.json').read_bytes())
    activation=json.loads((E/'REAL-QA-ACTIVATE-01.json').read_bytes())
    if (cfg.get('bundleSha256')!=pair['bundle'] or cfg.get('dllSha256')!=pair['dll'] or
            not activation.get('valid') or activation.get('selectedSchema')!=10 or
            ROOT/activation['candidateDirectory']!=Path(pointer['directory'])):
        raise SystemExit('Actual QA must already be the verified schema10/592 pair')
    path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();c=json.loads(before);previous=json.loads(before)['cases'][:68]
    inherited=[]
    for key,items in c.items():
        if key.endswith('Builds') and isinstance(items,list) and items and all(isinstance(x,dict) and set(x)=={'bundle','dll'} for x in items):
            if pair not in items:items.append(pair);inherited.append(key)
    intro='Sólo si indica DISPONIBLE EN TU SNAPSHOT. Ejecuta INICIAR-QA-RESTAURADO.cmd, usa su ACCESO-PRIVADO.txt y guía restaurada, selecciona Español y pulsa Ctrl+F5. No mezcles cuentas con QA original. Si el caso no está disponible, marca Bloqueado. La copia conserva tus cuentas y permisos: publicar requiere una concesión explícita del administrador mediante grupos (QA-14).'
    assert [v['id'] for v in c['cases'][-3:]]==['QA-69','QA-70','QA-71']
    for case in c['cases'][-3:]:case['steps'][0]=intro
    case67=next(v for v in c['cases'] if v['id']=='QA-67')
    old='la compartición/publicación sigue pendiente.'
    assert old in case67['steps'][-2]
    case67['steps'][-2]=case67['steps'][-2].replace(old,'la publicación compartida se verifica por separado con QA-69–71; aquí comprueba que las privadas no se heredan.')
    c['revision']='2026-10-18-grupo593-652'
    assert all(new==old for new,old in zip(c['cases'][:68],previous) if new['id']!='QA-67')
    path.write_bytes((json.dumps(c,ensure_ascii=False,indent=2)+'\n').replace('\n','\r\n').encode('utf-8'))
    receipt.write_text(json.dumps({'pair':pair,'inheritedBuildLists':inherited,'previous68Except67Unchanged':True,'changedCases':['QA-67','QA-69','QA-70','QA-71'],'change':'QA67 final ownership step clarifies shared publication now has separate QA69–71; QA69–71 availability introduction only. Expected results and all other steps unchanged. Guide fingerprints identify changed instructions; no user result storage is written.','beforeCatalogSha256':hashlib.sha256(before).hexdigest(),'afterCatalogSha256':sha(path),'caseCount':71,'availabilityRequiresSelectedSnapshot':True,'manualWascarResultsWritten':False,'qaDatabaseDml':False},indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'cases':71,'extendedFeatureLists':len(inherited),'previous68Except67Unchanged':True,'wascarResultsWritten':False}))
if __name__=='__main__':main()
