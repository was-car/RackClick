"""Enable exact832 pairs and six availability intros only after actual QA selection."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/quince-tandas-833-847'
def main():
    output=E/'QA-MATRIX-847.json';assert not output.exists()
    m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-773-832/CANDIDATA832-02.json').read_bytes());old=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json').read_bytes())
    pair=dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll']);source=dict(bundle=old['distributions']['frontend']['app.js'],dll=old['distributions']['server']['RackClick.Server.dll'])
    pointer=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes());cfg=json.loads((Path(pointer['directory'])/'manual-qa.json').read_bytes());activation=json.loads((E/'REAL-QA-ACTIVATE-01.json').read_bytes())
    assert activation['valid'] and activation['state']=='committed' and activation['selectedRevision']==832
    assert (ROOT/activation['candidateDirectory']).resolve()==Path(pointer['directory']).resolve()
    assert cfg['bundleSha256']==pair['bundle'] and cfg['dllSha256']==pair['dll']
    catalog=ROOT/'docs/QA-CASOS-WASCAR.json';before=catalog.read_bytes();c=json.loads(before);old_cases=json.loads(before)['cases'];inherited=[]
    for key,items in c.items():
        if key.endswith('Builds') and isinstance(items,list) and source in items and pair not in items:
            assert all(isinstance(x,dict) and set(x)=={'bundle','dll'} for x in items)
            items.append(pair);inherited.append(key)
    for key in ['rc9ExcelBuilds','rc9ExcelTextBuilds','rc9ExcelSafetyBuilds']:assert c[key]==[pair]
    assert len(c['cases'])==77
    intro='Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y ACCESO-PRIVADO.txt; elige Español y pulsa Ctrl+F5. Usa cuentas ficticias y otro perfil respecto a QA original. Si no está disponible, marca Bloqueado. Tus resultados y observaciones anteriores se conservan.'
    changed=['QA-60','QA-61','QA-62','QA-75','QA-76','QA-77']
    for new,prior in zip(c['cases'],old_cases):
        if new['id'] in changed:
            assert ('QA185 actual' in new['steps'][0] if int(new['id'][3:])<75 else 'QA712 actual' in new['steps'][0])
            new['steps'][0]=intro;assert new=={**prior,'steps':[intro]+prior['steps'][1:]}
        else:assert new==prior
    newline='\r\n' if b'\r\n' in before else '\n'
    c['revision']='2026-10-18-grupo833-847';catalog.write_bytes((json.dumps(c,ensure_ascii=False,indent=2)+'\n').replace('\n',newline).encode())
    data=dict(pair=pair,sourcePair=source,inheritedBuildLists=inherited,caseCount=77,unchangedCompleteCases=71,changedCases=changed,detailedStepsAndExpectedUnchanged=True,change='Six availability introductions only:75-77 now selected;60-62 stale185 intro corrected. Earlier results/notes remain stored by browser/import, never rewritten.',beforeCatalogSha256=hashlib.sha256(before).hexdigest(),afterCatalogSha256=hashlib.sha256(catalog.read_bytes()).hexdigest(),availabilityRequiresSelectedSnapshot=True,manualWascarResultsWritten=False,qaDatabaseDml=False)
    output.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(cases=77,inheritedLists=len(inherited),changedAvailabilityIntros=changed,manualWascarResultsWritten=False)))
if __name__=='__main__':main()
