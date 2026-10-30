"""Enable reviewed inherited GUI pairs after actual schema11 copy/selection only."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];E=ROOT/'evidence/s1-20261018/sesenta-tandas-713-772'
def main():
    output=E/'QA-MATRIX-772.json'
    if output.exists():raise SystemExit('Preserve QA matrix receipt')
    m=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-653-712/CANDIDATA712-FINAL02.json').read_bytes());old=json.loads((ROOT/'evidence/s1-20261018/sesenta-tandas-533-592/CANDIDATA592-FINAL02.json').read_bytes())
    pair=dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll']);source=dict(bundle=old['distributions']['frontend']['app.js'],dll=old['distributions']['server']['RackClick.Server.dll'])
    pointer=json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes());cfg=json.loads((Path(pointer['directory'])/'manual-qa.json').read_bytes());activation=json.loads((E/'REAL-QA-ACTIVATE-01.json').read_bytes())
    assert activation['valid'] and activation['selectedSchema']==11 and activation['state']=='committed'
    assert (ROOT/activation['candidateDirectory']).resolve()==Path(pointer['directory']).resolve()
    assert cfg['bundleSha256']==pair['bundle'] and cfg['dllSha256']==pair['dll']
    catalog=ROOT/'docs/QA-CASOS-WASCAR.json';before=catalog.read_bytes();c=json.loads(before);oldcases=json.loads(before)['cases'];inherited=[]
    for key,items in c.items():
        if key.endswith('Builds') and isinstance(items,list) and source in items and pair not in items:
            assert all(isinstance(x,dict) and set(x)=={'bundle','dll'} for x in items)
            items.append(pair);inherited.append(key)
    assert c['userPreferencesBuilds']==[pair]
    assert len(c['cases'])==74 and [x['id'] for x in c['cases'][-3:]]==['QA-72','QA-73','QA-74']
    intro='Sólo si indica DISPONIBLE EN TU SNAPSHOT. Ejecuta INICIAR-QA-RESTAURADO.cmd y usa su guía y ACCESO-PRIVADO.txt. Selecciona Español y pulsa Ctrl+F5. No mezcles cuentas con QA original. Si no está disponible, marca Bloqueado. No ejecutes manualmente una candidata de desarrollo.'
    for case in c['cases'][-3:]:
        assert 'NO ESTÁ DISPONIBLE' in case['steps'][0];case['steps'][0]=intro
    assert c['cases'][:71]==oldcases[:71]
    assert all(new=={**prior,'steps':[intro]+prior['steps'][1:]} for new,prior in zip(c['cases'][-3:],oldcases[-3:]))
    c['revision']='2026-10-18-grupo713-772';catalog.write_bytes((json.dumps(c,ensure_ascii=False,indent=2)+'\n').replace('\n','\r\n').encode())
    data=dict(pair=pair,sourcePair=source,inheritedBuildLists=inherited,caseCount=74,previous71Exact=True,changedCases=['QA-72','QA-73','QA-74'],change='Only availability introductions of QA72–74 changed; expected outcomes and detailed steps unchanged; inherited pairs require previous592 support and preserved sources/native proof.',beforeCatalogSha256=hashlib.sha256(before).hexdigest(),afterCatalogSha256=hashlib.sha256(catalog.read_bytes()).hexdigest(),availabilityRequiresSelectedSnapshot=True,manualWascarResultsWritten=False,qaDatabaseDml=False)
    output.write_bytes((json.dumps(data,indent=2)+'\n').encode());print(json.dumps(dict(cases=74,inheritedLists=len(inherited),manualWascarResultsWritten=False)))
if __name__=='__main__':main()
