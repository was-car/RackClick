"""Enable palette cases only after the coordinator selects and validates real QA12."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
E=ROOT/'evidence/s1-20261018/sesenta-tandas-970-1029'


def main():
    out=E/'QA-MATRIX-1029.json';assert not out.exists()
    activated=json.loads((E/'REAL-QA-ACTIVATE-01.json').read_bytes())
    validated=json.loads((E/'REAL-QA-VALIDATE-01.json').read_bytes())
    assert activated['valid'] and activated['state']=='committed' and activated['selectedRevision']==969
    assert validated['valid'] and validated['selectedRevision']==969
    target=json.loads((E/'CANDIDATA969-FIX02.json').read_bytes())
    previous=json.loads((ROOT/'evidence/s1-20261018/tanda-849/CANDIDATA849.json').read_bytes())
    pair=lambda m:dict(bundle=m['distributions']['frontend']['app.js'],dll=m['distributions']['server']['RackClick.Server.dll'])
    new,old=pair(target),pair(previous)
    directory=Path(json.loads((ROOT/'.local/qa-rc9/current.json').read_bytes())['directory'])
    assert directory.resolve()==(ROOT/activated['candidateDirectory']).resolve()
    cfg=json.loads((directory/'manual-qa.json').read_bytes())
    assert cfg['bundleSha256']==new['bundle'] and cfg['dllSha256']==new['dll']
    path=ROOT/'docs/QA-CASOS-WASCAR.json';before=path.read_bytes();catalog=json.loads(before);original=json.loads(before)
    assert len(catalog['cases'])==81
    inherited=[]
    for key,values in catalog.items():
        if key.endswith('Builds') and isinstance(values,list) and old in values and new not in values:
            assert all(isinstance(v,dict) and set(v)=={'bundle','dll'} for v in values)
            values.append(new);inherited.append(key)
    assert 'userPortColorsBuilds' not in catalog
    catalog['userPortColorsBuilds']=[new]
    introductions=[
      'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. La candidata969/esquema12 está seleccionada en una copia nueva. Ejecuta INICIAR-QA-RESTAURADO.cmd, abre su guía y usa sus credenciales privadas. Selecciona Español y pulsa Ctrl+F5; tus resultados anteriores se conservan.',
      'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa el QA restaurado969 con perfiles de navegador separados. Este guion comprueba la paleta; tus resultados de otros módulos se conservan.',
      'Sólo si la cabecera indica DISPONIBLE EN TU SNAPSHOT. Usa el QA restaurado969. La parte de fallo de red es opcional si puedes usar F12/Red/Offline en tu pestaña: si no localizas el control, anota Bloqueado para esa parte, sin afectar otros usuarios.'
    ]
    for case,intro in zip(catalog['cases'][78:],introductions):
        assert case['id'] in ['QA-79','QA-80','QA-81'] and case['feature']=='planned'
        case['feature']='userPortColorsGui';case['steps'][0]=intro
    assert catalog['cases'][:78]==original['cases'][:78]
    assert all(c['steps'][1:]==o['steps'][1:] and c['expected']==o['expected'] for c,o in zip(catalog['cases'][78:],original['cases'][78:]))
    catalog['revision']='2026-10-18-bloque970-1029'
    newline='\r\n' if b'\r\n' in before else '\n'
    path.write_bytes((json.dumps(catalog,ensure_ascii=False,indent=2)+'\n').replace('\n',newline).encode())
    generator=ROOT/'tools/windows/qa_guide.py';source=generator.read_bytes()
    anchor=b"        'adminGroupRelationsAnnouncementGui': catalog.get('adminGroupRelationsAnnouncementBuilds', []),"
    assert source.count(anchor)==1 and b"'userPortColorsGui':" not in source
    line=(b'\r\n' if b'\r\n' in source else b'\n')+b"        'userPortColorsGui': catalog.get('userPortColorsBuilds', []),"
    before_dir=E/'qa-guide/source-before';before_dir.mkdir(parents=True,exist_ok=False)
    (before_dir/'qa_guide.py').write_bytes(source)
    for name in ['qa_port_colors969.py','test_qa_relations_status848.py']:
        (before_dir/name).write_bytes((ROOT/'tools/tests'/name).read_bytes())
    generator.write_bytes(source.replace(anchor,anchor+line))
    record=dict(sourcePair=old,pair=new,inheritedBuildLists=inherited,caseCount=81,unchangedCompleteCases=78,
        changedCases=['QA-79','QA-80','QA-81'],changedFields=['feature','steps[0]'],otherStepsAndExpectedUnchanged=True,
        beforeCatalogSha256=hashlib.sha256(before).hexdigest(),afterCatalogSha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        manualWascarResultsWritten=False,qaDatabaseDml=False)
    with out.open('x',encoding='utf-8') as stream:stream.write(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(cases=81,inheritedLists=len(inherited),newlyAvailable=['QA-79','QA-80','QA-81'],manualResultsWritten=False)))


if __name__=='__main__':main()
